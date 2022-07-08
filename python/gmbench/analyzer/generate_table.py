# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import math
import sys
from collections import namedtuple

import gmbench.db


Result = namedtuple('Result', 'value bound feasible total optimal optima_known accuracy')
BestResult = namedtuple('BestResult', 'value bound optimal')


def init_subparser(subparsers):
    kinds = ('html', 'paper-small', 'paper-large', 'paper-dataset')
    parser = subparsers.add_parser('generate-table')
    parser.add_argument('--run', '-r', type=int, required=True, help='Specifies the run id')
    parser.add_argument('--kind', '-k', choices=kinds, required=True)
    parser.add_argument('--dataset', '-d')
    return parser


def get_result(db, run_id, method, dataset, checkpoint):
    cur = db.execute('SELECT value_avg, bound_avg, feasible, total, optimal, optima_known, accuracy_known_nodes_avg '
                     'FROM benchmark_per_dataset_pretty '
                     'WHERE run_id=? AND method=? AND dataset=? AND checkpoint=?',
                     (run_id, method, dataset, checkpoint))
    return Result(*cur.fetchone())


def get_methods(db):
    cur = db.execute('SELECT name FROM method ORDER BY name')
    for name, in cur:
        yield name


def get_datasets(db):
    cur = db.execute('SELECT name FROM dataset ORDER BY name')
    for name, in cur:
        yield name


def get_checkpoints(db):
    cur = db.execute('SELECT time FROM checkpoint ORDER BY time')
    for time, in cur:
        yield time


def materialize_view(db, run_id):
    # We materialize the view `main.benchmark_per_dataset_pretty` into
    # a temporary table `temp.benchmark_per_dataset_pretty`. Note that
    # later usage of unqualified `benchmark_per_dataset_pretty` will
    # use the temporary (hence fast) one.
    db.execute('CREATE TEMPORARY TABLE benchmark_per_dataset_pretty AS '
               '  SELECT * FROM benchmark_per_dataset_pretty '
               '  WHERE run_id = ?',
               (run_id,))


def generate_html_table(db, run_id, checkpoint, dataset):
    print(f'<table border><caption>{dataset} ({checkpoint}s)</caption>')
    print(f'<tr><th>method</th><th>avg value</th><th>avg bound</th><th>feasible</th><th>optimal</th></tr>')
    for method in get_methods(db):
        result = get_result(db, run_id, method, dataset, checkpoint)
        print(f'<tr><td>{method}</td><td>{result.value:,.1f}</td><td>{result.bound:,.1f}</td><td>{result.feasible}/{result.total}</td><td>{result.optimal}/{result.optima_known}</td></tr>')
    print(f'</table>')


def generate_html(args, db):
    materialize_view(db, args.run)
    print('<!DOCTYPE html5>')
    print('<html lang="en"><body><h1>Graph Matching Benchmark Results</h1>')

    for checkpoint in get_checkpoints(db):
        print(f'<h2>Checkpoint {checkpoint}s</h2>')
        for dataset in get_datasets(db):
            generate_html_table(db, args.run, checkpoint, dataset)

    print('</body></html>')


def generate_paper_table(db, run_id, columns, rows):
    materialize_view(db, run_id)

    # Fetch all results from the database.
    table = {}
    for method in rows:
        if method != '---':
            for dataset, checkpoint, _, _, _ in columns:
                result = get_result(db, run_id, method, dataset, checkpoint)
                table.setdefault((dataset, checkpoint), {})[method] = result

    # Compute the best values column-wise.
    for column_data in table.values():
        best_optimal = max(x.optimal for x in column_data.values())
        best_value   = min(x.value   for x in column_data.values())
        best_bound   = max(x.bound   for x in column_data.values())
        column_data['best'] = BestResult(optimal=best_optimal,
                                         value=best_value,
                                         bound=best_bound)

    # Format final table.
    for method in rows:
        if method == '---':
            print(r'\midrule')
            continue

        tex_cols = [f'\\Salg{{{method}}}']
        for col_idx, (dataset, checkpoint, has_dual, has_opt, has_acc) in enumerate(columns):
            result = table[dataset, checkpoint][method]

            if has_opt:
                if result.optimal >= table[dataset, checkpoint]['best'].optimal:
                    opt_pre = '\\bfseries '
                else:
                    opt_pre = ''
                opt = 100.0 * result.optimal / result.total
                tex_cols.append(f'{opt_pre}{opt:.0f}')

            if math.isfinite(result.value):
                val = result.value
                if val <= table[dataset, checkpoint]['best'].value + .51:
                    val_pre = '\\bfseries '
                else:
                    val_pre = ''
                if math.isfinite(val):
                    val = f'{val:.0f}'
                else:
                    val = '--'
                tex_cols.append(f'{val_pre}{val}')

                if has_dual:
                    bou = result.bound
                    if bou >= table[dataset, checkpoint]['best'].bound - .51:
                        bou_pre = '\\bfseries'
                    else:
                        bou_pre = ''
                    if math.isfinite(bou):
                        bou = f'{bou:.0f}'
                    else:
                        bou = '--'
                    tex_cols.append(f'{bou_pre}{bou}')

                if has_acc:
                    if result.accuracy is not None:
                        tex_cols.append(f'{100.0 * result.accuracy:.0f}')
                    else:
                        tex_cols.append('')
            else:
                cols = 1
                if has_dual:
                    cols += 1
                if has_acc:
                    cols += 1
                style = 'g' if col_idx % 2 == 0 else 'c'
                tex_cols.append('\\multicolumn{' + str(cols) + '}{' + style + '}{---*}')

        print(' & '.join(tex_cols), '\\\\')


def generate_paper_small(args, db):
    columns = (('hotel',            1,  False,   True,   True),
               ('house-dense',      1,  False,   True,   True),
               ('house-sparse',     1,  False,   True,   True),
               ('car',              1,  False,   True,   True),
               ('motor',            1,  False,   True,   True),
               ('opengm',           1,  False,   True,   False),
               ('caltech-small',    1,  False,   True,   True))
    rows = ('fgmd', 'fm', 'fw', 'ga', 'ipfps', 'ipfpu', 'lsm', 'mpm',
            'pm', 'rrwm', 'sm', 'smac',
            '---',
            'dd-ls0', 'dd-ls3', 'dd-ls4', 'fm-bca', 'hbp', 'mp', 'mp-fw', 'mp-mcf')
    generate_paper_table(db, args.run, columns, rows)


def generate_paper_large(args, db):
    columns = (('flow',             1,      True,   True,   False),
               ('worms',            1,      True,   True,   True),
              #('worms',            10,     True,   True,   True),
               ('caltech-large',    10,     True,   False,  True),
               ('caltech-large',    100,    True,   False,  True),
               ('pairs',            10,     True,   False,  True),
               ('pairs',            100,    True,   False,  True))
    rows = ('fm', 'fw',
            '---',
            'dd-ls0', 'dd-ls3', 'dd-ls4', 'fm-bca', 'mp', 'mp-fw', 'mp-mcf')
    generate_paper_table(db, args.run, columns, rows)


def generate_paper_dataset(args, db):
    if not args.dataset:
        print('Error: --kind=paper-dataset requires --dataset parameter', file=sys.stderr)
        sys.exit(1)

    rows = ('fgmd', 'fm', 'fw', 'ga', 'ipfps', 'ipfpu', 'lsm', 'mpm',
            'pm', 'rrwm', 'sm', 'smac',
            '---',
            'dd-ls0', 'dd-ls3', 'dd-ls4', 'fm-bca', 'hbp', 'mp', 'mp-fw',
            'mp-mcf')

    per_dataset_flags = {
        'caltech-large':    (False, True),
        'caltech-small':    (True,  True),
        'car':              (True,  True),
        'flow':             (True,  False),
        'hotel':            (True,  True),
        'house-dense':      (True,  True),
        'house-sparse':     (True,  True),
        'motor':            (True,  True),
        'opengm':           (True,  False),
        'pairs':            (False, True),
        'worms':            (True,  True),
    }

    has_opt, has_acc = per_dataset_flags[args.dataset]
    columns = [(args.dataset, time, True, has_opt, has_acc)
               for time in (1, 10, 100, 300)]

    generate_paper_table(db, args.run, columns, rows)


def execute(args):
    with gmbench.db.connect() as db:
        func_name = args.kind.replace('-', '_')
        globals()[f'generate_{func_name}'](args, db)
