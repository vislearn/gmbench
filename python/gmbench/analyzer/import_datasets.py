# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import json
import os
import os.path
import re

import gmbench.db


def init_subparser(subparsers):
    parser = subparsers.add_parser('import-datasets')
    parser.add_argument('paths', metavar='PATH', nargs='+',
                        help='Path to dataset files (*.dd)')
    return parser


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def insert(db, dataset, instance, optimum=None, groundtruth=None):
    if groundtruth is not None:
        groundtruth = json.dumps(groundtruth)

    cur = db.execute('INSERT OR IGNORE INTO dataset (name) VALUES (?)',
                     (dataset,))
    cur = db.execute('SELECT id FROM dataset WHERE name = ?',
                     (dataset,))
    dataset_id, = cur.fetchone()

    cur = db.execute('SELECT max(number) FROM instance WHERE dataset_id = ?',
                     (dataset_id,))
    num, = cur.fetchone()
    num = (num or 0) + 1

    cur = db.execute('SELECT id FROM instance WHERE dataset_id=? AND name=?',
                     (dataset_id, instance))

    if row := cur.fetchone():
        instance_id, = row
        if (optimum is not None or groundtruth is not None):
            print(f'Updating optimum/groundtruth for {dataset}/{instance}')
            db.execute('UPDATE instance SET optimum=?, groundtruth=? WHERE id=?',
                       (optimum, groundtruth, instance_id))
    else:
        print(f'Inserting instance {dataset}/{instance}')
        db.execute('INSERT OR IGNORE INTO instance (dataset_id, name, number, optimum, groundtruth) '
                   'VALUES                         (         ?,    ?,      ?,       ?,           ?)',
                   (dataset_id, instance, num, optimum, groundtruth))


def adjust_groundtruth(assignment):
    check = lambda x: ( (x is None) or
                        (type(x) is int) or
                        (type(x) is list and len(x) > 0) )
    assert all(check(x) for x in assignment)
    return [[x] if type(x) == int else x for x in assignment]


def find_dataset_instances(path):
    re_filename = re.compile(r'^(?P<instance>.+)\.dd(?:\.gz|\.xz)?')

    for root, dirs, files in os.walk(path):
        dataset = os.path.basename(root)
        for file in natural_sort(files):
            if m := re_filename.search(file):
                # Our file at hand is a dataset instance. Check if files for
                # optimal objective value and ground truth are also present.
                instance = m.group('instance')

                opt = None
                opt_file = os.path.join(root, instance + '.opt')
                if os.path.exists(opt_file):
                    with open(opt_file, 'rt') as f:
                        opt = float(f.read().strip())

                gt = None
                gt_file = os.path.join(root, instance + '.gt')
                if os.path.exists(gt_file):
                    with open(gt_file, 'rt') as f:
                        gt = adjust_groundtruth(json.load(f))

                yield dataset, instance, opt, gt


def execute(args):
    with gmbench.db.connect() as db:
        with db:
            for path in args.paths:
                for result in find_dataset_instances(path):
                    insert(db, *result)
