# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

#!/usr/bin/env python3

import gzip
import json
import os
import os.path
import sys

import gmbench.db


DATA_FILENAME = 'data.json.gz'


def init_subparser(subparsers):
    parser = subparsers.add_parser('import-benchmark')
    parser.add_argument('--date', '-d')
    parser.add_argument('--hardware', '-H', required=True)
    parser.add_argument('paths', metavar='PATH', nargs='+', help='Path to benchmark directory')
    return parser


def find_data_files(paths):
    for path in paths:
        for root, dirs, files in os.walk(path):
            if DATA_FILENAME in files:
                yield os.path.join(root, DATA_FILENAME)


def parse_data_file(filename):
    with gzip.open(filename, 'rt') as f:
        return json.load(f)


def fetch_hardware_id(db, hardware):
    cur = db.execute('SELECT id FROM hardware WHERE name=?', (hardware,))
    row = cur.fetchone()
    if not row:
        print('Error: Unknown hardware selector', hardware, file=sys.stderr)
        sys.exit(1)
    return row[0]


def insert_run(db, date, hardware_id):
    if not date:
        cur = db.execute('INSERT INTO run (hardware_id) VALUES (?)',
                         (hardware_id,))
    else:
        cur = db.execute('INSERT INTO run (date, hardware_id) VALUES (?, ?)',
                         (date, hardware_id))
    return cur.lastrowid


def fetch_method_id(db, method):
    cur = db.execute('SELECT id FROM method WHERE name=?', (method,))
    row = cur.fetchone()
    if not row:
        print('Error: Unknown method', method, file=sys.stderr)
        sys.exit(1)
    return row[0]


def fetch_instance_id(db, dataset, instance):
    cur = db.execute('SELECT instance.id '
                     'FROM instance '
                     'INNER JOIN dataset ON dataset.id = instance.dataset_id '
                     'WHERE dataset.name=? AND instance.name=?',
                     (dataset, instance))
    row = cur.fetchone()
    if not row:
        print(f'Error: Unknown dataset instance {dataset}/{instance}', file=sys.stderr)
        sys.exit(1)
    return row[0]


def insert_datapoints(db, method_id, instance_id, run_id, trial, datapoints):
    def gen():
        for iteration, dp in enumerate(datapoints):
            assignment_id = None
            if dp['assignment']:
                assignment = json.dumps(dp['assignment'])
                cur = db.execute('SELECT id FROM assignment WHERE value=?',
                                 (assignment,))
                if row := cur.fetchone():
                    assignment_id, = row
                else:
                    cur = db.execute('INSERT INTO assignment (value) VALUES (?)',
                                     (assignment,))
                    assignment_id = cur.lastrowid
                assert assignment_id is not None

            yield (run_id, method_id, instance_id, trial, iteration,
                   dp['time'], dp['value'], dp['bound'], assignment_id)

    db.executemany('INSERT INTO output (run_id, method_id, instance_id, trial, '
                   '                    iteration, time, value, bound, '
                   '                    assignment_id) '
                   'VALUES             (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   gen())


def execute(args):
    with gmbench.db.connect() as db:
        with db:
            hardware_id = fetch_hardware_id(db, args.hardware)
            run_id = insert_run(db, args.date, hardware_id)

            for filename in find_data_files(args.paths):
                print(f'Processing file “{filename}”...')
                data = parse_data_file(filename)
                method = data['method']
                dataset = data['dataset']
                trial = data['trial']
                instance = dataset + str(data['instance'])

                method_id = fetch_method_id(db, method)
                instance_id = fetch_instance_id(db, dataset, instance)
                insert_datapoints(db, method_id, instance_id, run_id, trial,
                                  data['datapoints'])

        print(f'Run {run_id} imported successfully.')
