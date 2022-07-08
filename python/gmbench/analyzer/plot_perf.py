# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import matplotlib.pyplot as plt

import gmbench.db

FIXED_COLORS = {
    'fm-bca':   'C0',
    'fm':       'C1',
    'mp-fw':    'C2',
    'dd-ls0':   'C3',
    'dd-ls3':   'C4',
    'mp':       'C5',
    'dd-ls4':   'C6',
    'mp-mcf':   'C7',
    'fw':       'C8',
    'hbp':      'C9',
    'ga':       'C10',
}


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
                CASE WHEN min(output.time) < :min_runtime THEN :min_runtime
                     ELSE min(output.time)
                END AS time
            FROM output_postprocessed AS output
            INNER JOIN instance ON instance.id = output.instance_id
            INNER JOIN best ON best.instance_id = output.instance_id
            WHERE output.run_id = :run_id
              AND output.value <= best.value + :optimality_tolerance * abs(best.value)
              AND (:dataset_id IS NULL OR instance.dataset_id = :dataset_id)
            GROUP BY output.run_id, output.method_id, output.instance_id),
        best_opt_per_instance AS (
            SELECT run_id, instance_id, min(time) AS time
            FROM opt_per_instance AS opt
            GROUP BY opt.run_id, opt.instance_id),
        perf_ratio AS (
            SELECT
                opt.run_id,
                opt.method_id,
                opt.instance_id,
                opt.time / best_opt.time AS perf_ratio
            FROM opt_per_instance AS opt
            INNER JOIN best_opt_per_instance AS best_opt ON best_opt.run_id = opt.run_id
                                                        AND best_opt.instance_id = opt.instance_id
            WHERE opt.time / best_opt.time IS NOT NULL)
    SELECT
        method.name             AS method,
        perf_ratio.perf_ratio   AS perf_ratio,
        row_number() OVER win   AS instances
    FROM perf_ratio
    INNER JOIN method ON method.id = perf_ratio.method_id
    WHERE (:max_perf_ratio IS NULL OR perf_ratio.perf_ratio < :max_perf_ratio)
    WINDOW win AS (PARTITION BY perf_ratio.method_id
                   ORDER BY perf_ratio.perf_ratio
                   ROWS UNBOUNDED PRECEDING)
'''


def init_subparser(subparsers):
    parser = subparsers.add_parser('plot-perf')
    parser.add_argument('--run', '-r', required=True)
    parser.add_argument('--dataset', '-d')
    parser.add_argument('--min-runtime', '-m', type=float)
    parser.add_argument('--optimality-tolerance', '-t', type=float, default=0)
    parser.add_argument('--logscale', '-l', action='store_true')
    parser.add_argument('--width', '-W', type=float)
    parser.add_argument('--height', '-H', type=float)
    parser.add_argument('--max-perf-ratio', '-M', type=float)
    parser.add_argument('--no-legend', action='store_true')
    parser.add_argument('--output', '-o')
    return parser


def compute_area(method_data):
    x = method_data['x']
    y = method_data['y']
    assert len(x) == len(y)

    area = 0
    for i in range(1, len(x)):
        assert x[i-1] <= x[i]
        area += y[i-1] * (x[i] - x[i-1])

    return area


def make_rectangular(method_data):
    x = method_data['x']
    y = method_data['y']
    assert len(x) == len(y)

    x_new, y_new = [1], [0]
    for i in range(len(x)):
        x_new.append(x[i])
        y_new.append(y_new[-1])

        x_new.append(x[i])
        y_new.append(y[i])

    return x_new, y_new


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
                                         'dataset_id': dataset_id,
                                         'min_runtime': args.min_runtime,
                                         'optimality_tolerance': args.optimality_tolerance / 100.0,
                                         'max_perf_ratio': args.max_perf_ratio})


            # Fetch data from database.
            data = {}
            for row in cur:
                method = row['method']
                if not method in data:
                    data[method] = {'method': method, 'x': [], 'y': []}
                data[method]['x'].append(row['perf_ratio'])
                data[method]['y'].append(row['instances'] / total * 100)

            # Ensure that data points start and end at the roughly the same
            # position in x space.
            for method_data in data.values():
                if method_data['x'][0] > 1.05:
                    method_data['x'].insert(0, 1.0)
                    method_data['y'].insert(0, 0.0)
                if method_data['x'][-1] < 1e3:
                    method_data['x'].append(1e3)
                    method_data['y'].append(method_data['y'][-1])

            # Assign color to methods before sorting methods by performance.
            for method, method_data in data.items():
                if c := FIXED_COLORS.get(method):
                    method_data['color'] = c

            # Sort methods so that the better performing ones are first.
            data = sorted(data.values(), key=compute_area, reverse=True)

            if args.width and args.height:
                plt.figure(figsize=(args.width, args.height))
            else:
                plt.figure()

            plt.title(args.dataset)

            plt.xlabel('ratio to best performance $\\tau$')
            plt.ylabel('solving probability $\\rho(\\tau)$ in %')

            for i, method_data in enumerate(data):
                if i < 6:
                    kwargs = {'linewidth': 3,
                              'label': method_data['method'],
                              'color': method_data.get('color'),
                              'zorder': 10-i}
                else:
                    kwargs = {'linewidth': 2,
                              'color': '#aaaaaa',
                              'alpha': .4,
                              'zorder': 1}
                x, y = make_rectangular(method_data)
                plt.plot(x, y, **kwargs)

            if args.logscale:
                plt.xscale('log')

            plt.grid(color='#888888', linestyle=':')
            plt.xlim(1, args.max_perf_ratio)
            plt.ylim(0, 100)

            if not args.no_legend:
                plt.legend(loc='lower right').set_zorder(20)

            if args.output:
                plt.tight_layout()
                plt.savefig(args.output)
            else:
                plt.show()
