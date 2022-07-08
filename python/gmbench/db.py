# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import os
import os.path
import sqlite3
import contextlib


DB_FILE = 'benchmark.db'

DB_SCHEMA = '''

CREATE TABLE IF NOT EXISTS dataset (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    UNIQUE(name));

CREATE TABLE IF NOT EXISTS instance (
    id INTEGER PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES dataset,
    number INTEGER,
    name TEXT NOT NULL,
    optimum REAL,
    groundtruth TEXT,
    UNIQUE(dataset_id, number),
    UNIQUE(dataset_id, name));

CREATE TABLE IF NOT EXISTS method (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    UNIQUE(name));

CREATE TABLE IF NOT EXISTS hardware (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    UNIQUE(name));

CREATE TABLE IF NOT EXISTS assignment (
    id INTEGER PRIMARY KEY,
    value TEXT NOT NULL,
    UNIQUE(value));

CREATE TABLE IF NOT EXISTS run (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    hardware_id INTEGER NOT NULL REFERENCES hardware);

CREATE TABLE IF NOT EXISTS output (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES run,
    method_id INTEGER NOT NULL REFERENCES method,
    instance_id INTEGER NOT NULL REFERENCES instance,
    trial INTEGER NOT NULL,
    iteration INTEGER NOT NULL,
    time REAL NOT NULL, -- seconds
    value REAL NOT NULL,
    bound REAL NOT NULL,
    assignment_id INTEGER REFERENCES assignment,
    CHECK((value >= 1e999) = (assignment_id IS NULL)));

CREATE INDEX IF NOT EXISTS output_index_1 ON output (run_id, method_id, instance_id, trial, iteration);
CREATE INDEX IF NOT EXISTS output_index_2 ON output (run_id, method_id, instance_id, iteration);

CREATE VIEW IF NOT EXISTS output_trial_diff_to_best AS
    SELECT *, time - min(time) OVER win AS time_diff
    FROM output
    WINDOW win AS (PARTITION BY run_id, method_id, instance_id, iteration);

CREATE VIEW IF NOT EXISTS output_trial_max_diff_to_best AS
    SELECT
        run_id, method_id, instance_id, trial,
        max(time_diff) AS time_diff_max
    FROM output_trial_diff_to_best
    GROUP BY run_id, method_id, instance_id, trial;

CREATE VIEW IF NOT EXISTS output_trial_diff_range AS
    SELECT
        run_id                  AS run_id,
        method_id               AS method_id,
        instance_id             AS instance_id,
        iteration               AS iteration,
        max(time)  - min(time)  AS time_diff,
        max(value) - min(value) AS value_diff
    FROM output
    GROUP BY run_id, method_id, instance_id, iteration;

CREATE TABLE IF NOT EXISTS output_postprocessed (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES run,
    method_id INTEGER NOT NULL REFERENCES method,
    instance_id INTEGER NOT NULL REFERENCES instance,
    time REAL NOT NULL, -- seconds
    value REAL NOT NULL,
    bound REAL NOT NULL,
    assignment_id INTEGER REFERENCES assignment,
    accuracy_all_nodes REAL,
    accuracy_known_nodes REAL,
    CHECK((value >= 1e999) = (assignment_id IS NULL)));

CREATE INDEX IF NOT EXISTS output_postprocessed_index_1 ON output_postprocessed (run_id, method_id, instance_id, time);

CREATE TABLE IF NOT EXISTS checkpoint (
    time INT NOT NULL, -- seconds
    UNIQUE(time));

CREATE VIEW IF NOT EXISTS output_checkpointed AS
    WITH temp AS (
        SELECT
            checkpoint.time             AS checkpoint,
            output.id                   AS id,
            output.run_id               AS run_id,
            output.method_id            AS method_id,
            output.instance_id          AS instance_id,
            output.time                 AS time,
            output.value                AS value,
            output.bound                AS bound,
            output.assignment_id        AS assignment_id,
            output.accuracy_all_nodes   AS accuracy_all_nodes,
            output.accuracy_known_nodes AS accuracy_known_nodes,
            row_number() OVER win AS rn
        FROM checkpoint
        INNER JOIN output_postprocessed AS output ON output.time <= checkpoint.time
        WINDOW win AS (PARTITION BY checkpoint.time, output.run_id,
                                    output.method_id, output.instance_id
                       ORDER BY output.time DESC))
    SELECT checkpoint, id, run_id, method_id, instance_id, time, value, bound,
           assignment_id, accuracy_all_nodes, accuracy_known_nodes
    FROM temp
    WHERE rn = 1;

CREATE VIEW IF NOT EXISTS benchmark AS
    SELECT
        checkpoint.time AS checkpoint,
        run.id          AS run_id,
        method.id       AS method_id,
        instance.id     AS instance_id,
        output.id       AS output_id,
        output.value,
        output.bound,
        output.assignment_id,
        output.accuracy_all_nodes,
        output.accuracy_known_nodes,
        CASE WHEN instance.optimum IS NOT NULL
            THEN coalesce(output.value <= instance.optimum + 0.1 / 100.0 * abs(instance.optimum), 0)
            ELSE NULL
        END AS optimal
    FROM run, method, instance, checkpoint
    LEFT OUTER JOIN output_checkpointed AS output
        ON  output.run_id      = run.id
        AND output.method_id   = method.id
        AND output.instance_id = instance.id
        AND output.checkpoint  = checkpoint.time;

CREATE VIEW IF NOT EXISTS benchmark_pretty AS
    SELECT
        benchmark.run_id                    AS run_id,
        method.name                         AS method,
        dataset.name                        AS dataset,
        instance.name                       AS instance,
        benchmark.checkpoint                AS checkpoint,
        coalesce(benchmark.value,  1e999)   AS value,
        coalesce(benchmark.bound, -1e999)   AS bound,
        benchmark.optimal                   AS optimal,
        benchmark.accuracy_all_nodes        AS accuracy_all_nodes,
        benchmark.accuracy_known_nodes      AS accuracy_known_nodes
    FROM benchmark
    INNER JOIN method   ON method.id   = benchmark.method_id
    INNER JOIN instance ON instance.id = benchmark.instance_id
    INNER JOIN dataset  ON dataset.id  = instance.dataset_id;

CREATE VIEW IF NOT EXISTS benchmark_per_dataset AS
    SELECT
        benchmark.run_id                        AS run_id,
        benchmark.method_id                     AS method_id,
        dataset.id                              AS dataset_id,
        benchmark.checkpoint                    AS checkpoint,
        avg(coalesce(benchmark.value,  1e999))  AS value_avg,
        avg(coalesce(benchmark.bound, -1e999))  AS bound_avg,
        count(benchmark.value)                  AS feasible,
        count(*)                                AS total,
        coalesce(sum(benchmark.optimal), 0)     AS optimal,
        count(instance.optimum)                 AS optima_known,
        avg(benchmark.accuracy_all_nodes)       AS accuracy_all_nodes_avg,
        avg(benchmark.accuracy_known_nodes)     AS accuracy_known_nodes_avg,
        count(instance.groundtruth)             AS groundtruth_known
    FROM benchmark
    INNER JOIN instance ON instance.id = benchmark.instance_id
    INNER JOIN dataset  ON dataset.id  = instance.dataset_id
    GROUP BY benchmark.run_id, benchmark.method_id, dataset.id, checkpoint;

CREATE VIEW IF NOT EXISTS benchmark_per_dataset_pretty AS
    SELECT
        bpd.run_id,
        method.name     AS method,
        dataset.name    AS dataset,
        bpd.checkpoint,
        bpd.value_avg,
        bpd.bound_avg,
        bpd.feasible,
        bpd.total,
        bpd.optimal,
        bpd.optima_known,
        CASE WHEN bpd.feasible == bpd.total
            THEN bpd.accuracy_all_nodes_avg
            ELSE NULL
        END AS accuracy_all_nodes_avg,
        CASE WHEN bpd.feasible == bpd.total
            THEN bpd.accuracy_known_nodes_avg
            ELSE NULL
        END AS accuracy_known_nodes_avg
    FROM benchmark_per_dataset AS bpd
    INNER JOIN method   ON method.id   = bpd.method_id
    INNER JOIN dataset  ON dataset.id  = bpd.dataset_id;

INSERT OR IGNORE INTO method (name) VALUES
    ('dd-ls0'),
    ('dd-ls3'),
    ('dd-ls4'),
    ('fgmd'),
    ('fm-bca'),
    ('fm'),
    ('fw'),
    ('ga'),
    ('hbp'),
    ('ipfps'),
    ('ipfpu'),
    ('lsm'),
    ('mp'),
    ('mp-fw'),
    ('mpm'),
    ('mp-mcf'),
    ('pm'),
    ('rrwm'),
    ('sm'),
    ('smac');

INSERT OR IGNORE INTO checkpoint (time) VALUES (1);
INSERT OR IGNORE INTO checkpoint (time) VALUES (10);
INSERT OR IGNORE INTO checkpoint (time) VALUES (100);
INSERT OR IGNORE INTO checkpoint (time) VALUES (300);

CREATE VIEW IF NOT EXISTS verification_missing_instance_in_run AS
    SELECT
        run.id          AS run_id,
        instance.id     AS instance_id,
        instance.name   AS instance
    FROM run, instance
    LEFT OUTER JOIN output ON output.run_id = run.id
                          AND output.instance_id == instance.id
    WHERE output.id IS NULL;

CREATE VIEW IF NOT EXISTS verification_missing_method_in_run AS
    SELECT
        run.id          AS run_id,
        method.id       AS method_id,
        method.name     AS method
    FROM run, method
    LEFT OUTER JOIN output ON output.run_id = run.id
                          AND output.method_id = method.id
    WHERE output.id is null;

CREATE VIEW IF NOT EXISTS verification_missing_output_in_run AS
    SELECT
        run.id          AS run_id,
        method.id       AS method_id,
        method.name     AS method,
        instance.id     AS instance_id,
        instance.name   AS instance
    FROM run, method, instance
    LEFT OUTER JOIN output ON output.run_id = run.id
                          AND output.method_id = method.id
                          AND output.instance_id = instance.id
    WHERE output.id IS NULL;

CREATE VIEW IF NOT EXISTS verification_missing_trial_in_run AS
    WITH
        trial AS (SELECT DISTINCT run_id, trial FROM output),
        trial_count AS (
            SELECT run_id, method_id, instance_id, trial, 1 AS present
            FROM output
            GROUP BY run_id, method_id, instance_id, trial),
        helper_table AS (
            SELECT
                trial.run_id                            AS run_id,
                method.id                               AS method_id,
                method.name                             AS method,
                instance.id                             AS instance_id,
                instance.name                           AS instance,
                sum(trial_count.present IS NOT NULL)    AS count,
                count(*)                                AS total
            FROM trial, method, instance
            LEFT OUTER JOIN trial_count ON trial_count.run_id      = trial.run_id
                                       AND trial_count.method_id   = method.id
                                       AND trial_count.instance_id = instance.id
                                       AND trial_count.run_id      = trial.run_id
                                       AND trial_count.trial       = trial.trial
            GROUP BY trial.run_id, method.name, instance.name)
    SELECT *
    FROM helper_table
    WHERE count > 0 AND count < total;

CREATE VIEW IF NOT EXISTS verification_invalid_value_or_bound AS
    SELECT
        output.run_id   AS run_id,
        instance.id     AS instance_id,
        instance.name   AS instance,
        min(value)      AS value_min,
        max(bound)      AS bound_max,
        max(bound) - min(value) AS diff
    FROM output
    INNER JOIN instance ON instance.id = output.instance_id
    GROUP BY output.run_id, instance.id
    HAVING min(value) < max(bound) - 0.05;

CREATE VIEW IF NOT EXISTS verification_invalid_optima AS
    SELECT
        output.run_id       AS run_id,
        instance.id         AS instance_id,
        instance.name       AS instance,
        instance.optimum    AS optimum,
        min(output.value)   AS value_min
    FROM output
    INNER JOIN instance ON instance.id = output.instance_id
    GROUP BY output.run_id, instance.id
    HAVING value_min < instance.optimum - 0.05;

CREATE VIEW IF NOT EXISTS verification_nondeterminism AS
    SELECT
        o.run_id            AS run_id,
        o.method_id         AS method_id,
        method.name         AS method, 
        o.instance_id       AS instance_id,
        instance.name       AS instance,
        max(o.value_diff)   AS value_diff_max,
        max(o.time_diff)    AS time_diff_max
    FROM output_trial_diff_range AS o
    INNER JOIN method ON method.id = o.method_id
    INNER JOIN instance ON instance.id = o.instance_id
    GROUP BY run_id, method_id, instance_id
    HAVING value_diff_max > 0 OR time_diff_max > 10;

CREATE VIEW IF NOT EXISTS temp as select run_id, method_id, instance_id, trial, avg(time_diff) from output_trial_diff_to_best group by run_id, method_id, instance_id, trial;
'''


@contextlib.contextmanager
def connect(execute_schema=True):
    db = sqlite3.connect('benchmark.db')
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA temp_store = MEMORY')
        db.execute('PRAGMA journal_mode = WAL')
        db.execute('PRAGMA foreign_keys = 1')

        if execute_schema:
            db.executescript(DB_SCHEMA)

        yield db
    except:
        raise
    else:
        # If no exception was raised while the database was passed to the user,
        # we do some maintanence before closing the database.
        # See <https://www.sqlite.org/lang_analyze.html#req>.
        db.execute('PRAGMA optimize')
    finally:
        db.close()
