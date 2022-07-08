# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import gzip
import json
import math
import sys

import gmbench.db
import gmbench.perf


def cleanup_dict_entry(dictionary, key, func):
    dictionary[key] = func(dictionary[key])


def convert_to_bool(v):
    if v is not None:
        assert v == 0 or v == 1
        return bool(v)


def convert_from_json(value):
    if value is not None:
        return json.loads(value)


def cleanup_value(value):
    return value if value is not None else math.inf


def cleanup_bound(value):
    return value if value is not None else -math.inf


def select_algorithms(db):
    cur = db.execute('SELECT name FROM method ORDER BY name')
    return [row['name'] for row in cur]


def select_checkpoints(db):
    cur = db.execute('SELECT time FROM checkpoint ORDER BY time')
    return [row['time'] for row in cur]


def select_datasets(db):
    cur = db.execute('''
        SELECT
            dataset.name AS dataset,
            instance.number,
            instance.name,
            instance.optimum,
            instance.groundtruth
        FROM instance
        INNER JOIN dataset ON dataset.id = instance.dataset_id
        ORDER BY dataset.name, instance.number, instance.name
    ''')

    data = {}
    for row in cur:
        value = {
            k: row[k] for k in row.keys()
            if k not in ('dataset', )
        }

        cleanup_dict_entry(value, 'groundtruth', convert_from_json)

        data.setdefault(row['dataset'], {}) \
            .setdefault('instances', []).append(value)

    for dataset in data.values():
        instances = dataset['instances']
        dataset['total'] = len(instances)
        dataset['optima_known'] = sum(i['optimum'] is not None for i in instances)
        dataset['groundtruth_known'] = sum(i['groundtruth'] is not None for i in instances)

    return data


def select_results_per_instance(db, run_id):
    cur = db.execute('SELECT * FROM benchmark_pretty WHERE run_id = ?',
                     (run_id,))
    data = {}
    for row in cur:
        value = {
            k: row[k] for k in row.keys()
            if k not in ('checkpoint', 'dataset', 'instance', 'run_id')
        }

        cleanup_dict_entry(value, 'value', cleanup_value)
        cleanup_dict_entry(value, 'bound', cleanup_bound)
        cleanup_dict_entry(value, 'optimal', convert_to_bool)

        d = data.setdefault(row['checkpoint'], {}) \
                .setdefault(row['dataset'],    {}) \
                .setdefault(row['instance'],   {})
        assert row['method'] not in d
        d[row['method']] = value

    return data


def select_results_per_dataset(db, run_id):
    cur = db.execute('SELECT * FROM benchmark_per_dataset_pretty WHERE run_id = ?',
                     (run_id,))
    data = {}
    for row in cur:
        value = {
            k: row[k] for k in row.keys()
            if k not in ('checkpoint', 'dataset', 'optimum_known', 'run_id', 'total')
        }

        d = data.setdefault(row['checkpoint'], {}) \
                .setdefault(row['dataset'],    {})
        assert row['method'] not in d
        d[row['method']] = value

    return data


def construct_performance_plot_data(db, run_id):
    result = {'all': gmbench.perf.compute_performance_plot_data(db, run_id)}

    cur = db.execute('SELECT id, name FROM dataset')
    for row in cur:
        dataset_id, dataset = row
        result[dataset] = gmbench.perf.compute_performance_plot_data(db, run_id, dataset_id)

    return result


def construct_export_dict(db, run_id):
    return {
        'algorithms': select_algorithms(db),
        'checkpoints': select_checkpoints(db),
        'datasets': select_datasets(db),
        'results': {
            'per_instance': select_results_per_instance(db, run_id),
            'per_dataset': select_results_per_dataset(db, run_id),
        },
        'performance_plot_parameters': {
            'max_perf_ratio': gmbench.perf.DEFAULT_MAX_PERF_RATIO,
            'min_runtime': gmbench.perf.DEFAULT_MIN_RUNTIME,
            'optimality_tolerance': gmbench.perf.DEFAULT_OPTIMALITY_TOLERANCE,
        },
        'performance_plot_data': construct_performance_plot_data(db, run_id),
    }


def init_subparser(subparsers):
    parser = subparsers.add_parser('export')
    parser.add_argument('--run', '-r', type=int, required=True)
    parser.add_argument('--output', '-o', required=True)
    parser.add_argument('--compress', '-c', action='store_true')
    return parser


def execute(args):
    open_func = gzip.open if args.compress else open
    with open_func(args.output, 'wt') as f:
        with gmbench.db.connect() as db:
            with db:
                obj = construct_export_dict(db, args.run)
        json.dump(obj, f, indent=4)
        f.write('\n')
