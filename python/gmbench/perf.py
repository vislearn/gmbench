# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

DEFAULT_MIN_RUNTIME = 0.01
DEFAULT_OPTIMALITY_TOLERANCE = 0.1 # percent
DEFAULT_MAX_PERF_RATIO = 1000

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
            WHERE opt.time / best_opt.time IS NOT NULL),
        final_with_duplicates AS (
            SELECT
                method.name             AS method,
                perf_ratio.perf_ratio   AS perf_ratio,
                row_number() OVER win   AS instances
            FROM perf_ratio
            INNER JOIN method ON method.id = perf_ratio.method_id
            WHERE (:max_perf_ratio IS NULL OR perf_ratio.perf_ratio < :max_perf_ratio)
            WINDOW win AS (PARTITION BY perf_ratio.method_id
                           ORDER BY perf_ratio.perf_ratio
                           ROWS UNBOUNDED PRECEDING))
    SELECT method, perf_ratio, max(instances) AS instances
    FROM final_with_duplicates
    GROUP BY method, perf_ratio
'''


def compute_area(method_data, max_perf_ratio):
    x = method_data['x']
    y = method_data['y']
    assert len(x) == len(y)

    area = 0
    for i in range(1, len(x)):
        assert x[i] < max_perf_ratio + 1e-8
        assert x[i-1] <= x[i]
        area += y[i-1] * (x[i] - x[i-1])
    area += y[-1] * (max_perf_ratio - x[-1])

    return area


def compute_performance_plot_data(db, run_id, dataset_id=None,
                                  max_perf_ratio=None,
                                  min_runtime=None,
                                  optimality_tolerance=None):
    if max_perf_ratio is None:
        max_perf_ratio = DEFAULT_MAX_PERF_RATIO
    if min_runtime is None:
        min_runtime = DEFAULT_MIN_RUNTIME
    if optimality_tolerance is None:
        optimality_tolerance = DEFAULT_OPTIMALITY_TOLERANCE

    cur = db.execute('SELECT count(*) FROM instance '
                     'WHERE :dataset_id IS NULL OR dataset_id = :dataset_id',
                     {'dataset_id': dataset_id})
    total, = cur.fetchone()

    cur = db.execute(SQL_QUERY, {'run_id': run_id,
                                 'dataset_id': dataset_id,
                                 'min_runtime': min_runtime,
                                 'max_perf_ratio': max_perf_ratio,
                                 'optimality_tolerance': optimality_tolerance / 100.0})

    # Fetch data from database.
    data = {}
    for row in cur:
        method = row['method']
        if not method in data:
            data[method] = {'x': [], 'y': []}
        data[method]['x'].append(row['perf_ratio'])
        data[method]['y'].append(row['instances'] / total * 100)

    # Augment data by additional information.
    for method_data in data.values():
        method_data['area'] = compute_area(method_data, max_perf_ratio)

    return data
