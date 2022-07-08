# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

import gmbench.db


SQL_QUERY = '''
    WITH
        best_observed AS (
            SELECT instance_id, min(value) AS value
            FROM output_postprocessed
            WHERE run_id = :run_id
            GROUP BY instance_id),
        best_known AS (
            SELECT id AS instance_id, optimum AS value
            FROM instance
            WHERE optimum IS NOT NULL),
        best_union AS (
            SELECT * FROM best_observed
            UNION ALL
            SELECT * FROM best_known),
        best AS (
            SELECT instance_id, max(value) AS value
            FROM best_union
            GROUP BY instance_id),
        opt_per_instance AS (
            SELECT
                output.run_id,
                output.method_id,
                output.instance_id,
                min(output.time) AS time
            FROM output_postprocessed AS output
            INNER JOIN instance ON instance.id = output.instance_id
            INNER JOIN best ON best.instance_id = output.instance_id
            WHERE output.run_id = :run_id
              AND output.value <= best.value + 0.1 / 100.0 * abs(best.value)
              AND (:dataset_id IS NULL OR instance.dataset_id = :dataset_id)
            GROUP BY output.run_id, output.method_id, output.instance_id)
    SELECT
        method.name AS method,
        sum(opt.time) OVER win AS opt_time,
        row_number() OVER win AS opt_num
    FROM opt_per_instance AS opt
    INNER JOIN method ON method.id = opt.method_id
    WINDOW win AS (PARTITION BY opt.method_id
                   ORDER BY opt.time
                   ROWS UNBOUNDED PRECEDING)
'''


def init_subparser(subparsers):
    parser = subparsers.add_parser('plot-cactus')
    parser.add_argument('--run', '-r', required=True)
    parser.add_argument('--dataset', '-d')
    parser.add_argument('--logscale', '-l', action='store_true')
    parser.add_argument('--output', '-o')
    return parser


def execute(args):
    with gmbench.db.connect() as db:
        with db:
            dataset_id = None
            if args.dataset:
                cur = db.execute('SELECT id FROM dataset WHERE name = ?',
                                 (args.dataset,))
                dataset_id, = cur.fetchone()

            cur = db.execute('SELECT count(*) FROM instance '
                             'WHERE :dataset_id IS NULL OR dataset_id = :dataset_id',
                             {'dataset_id': dataset_id})
            total, = cur.fetchone()

            cur = db.execute(SQL_QUERY, {'run_id': args.run,
                                         'dataset_id': dataset_id})

            data = {}
            for row in cur:
                data.setdefault(row['method'], []).append((row['opt_time'], row['opt_num']))

            plt.figure()

            plt.title(args.dataset)
            plt.xlabel('cumulative runtime (s)')
            plt.ylabel(f'solved instances (out of {total})')

            # enforce integer ticks on y axis
            plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))

            for method, times in data.items():
                if False and not (method.startswith('mp-') or method.startswith('fm') or method.startswith('dd-') or method == 'fw'):
                    continue
                x = [x[0] for x in data[method]]
                y = [x[1] for x in data[method]]
                plt.plot(x, y, label=method)

            if args.logscale:
                plt.xlim(1e-1, 1e3)
                plt.xscale('log')
            plt.legend()

            if args.output:
                plt.savefig(args.output)
            else:
                plt.show()
