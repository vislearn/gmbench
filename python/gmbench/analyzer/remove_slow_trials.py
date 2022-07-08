# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import sys

import gmbench.db

SQL_UNFINISHED_TRIALS = '''
WITH
    trial AS (
        SELECT DISTINCT run_id, trial
        FROM output WHERE run_id = :run_id),
    presence AS (
        SELECT method.id AS method_id,
               method.name AS method,
               dataset.name AS dataset,
               instance.id AS instance_id,
               instance.name AS instance,
               trial.trial AS trial,
               count(output.id) > 0 AS present
        FROM trial, method, instance
        INNER JOIN dataset ON dataset.id = instance.dataset_id
        LEFT OUTER JOIN output ON output.method_id = method.id
                              AND output.instance_id = instance.id
                              AND output.run_id = trial.run_id
                              AND output.trial  = trial.trial
        GROUP BY trial.run_id, trial.trial, method.id, instance.id),
    count_helper AS (
        SELECT *,
            sum(present) OVER win AS count,
            count(*) OVER win AS total
        FROM presence
        WINDOW win AS (PARTITION BY method_id, instance_id))
SELECT *
FROM count_helper
WHERE present = 0 AND count > 0 AND count < total
'''

SQL_SLOW_TRIALS = '''
SELECT method.name AS method,
       dataset.name AS dataset,
       instance.name AS instance,
       o.trial AS trial
FROM output_trial_max_diff_to_best AS o
INNER JOIN method ON method.id = o.method_id
INNER JOIN instance ON instance.id = o.instance_id
INNER JOIN dataset ON dataset.id = instance.dataset_id
WHERE run_id = :run_id AND time_diff_max > 10
'''


def process_row(row):
    print(f"rm -r 'benchmark/{row['trial']}/{row['method']}/{row['dataset']}/{row['instance']}'")


def init_subparser(subparsers):
    parser = subparsers.add_parser('remove-slow-trials')
    parser.add_argument('--run', '-r', required=True)
    return parser


def execute(args):
    with gmbench.db.connect() as db:
        with db:
            cur = db.execute(SQL_UNFINISHED_TRIALS, {'run_id': args.run})
            for row in cur:
                process_row(row)

            cur = db.execute(SQL_SLOW_TRIALS, {'run_id': args.run})
            for row in cur:
                process_row(row)
