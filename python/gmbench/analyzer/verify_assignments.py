# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import json
import multiprocessing
import sys
import time

import gmbench.db
import gmbench.verification


SQL = '''
    SELECT
        dataset.name        AS dataset,
        instance.name       AS instance,
        method.name         AS method,
        output.run_id       AS run_id,
        output.time         AS time,
        output.value        AS value,
        assignment.value    AS assignment
    FROM output_postprocessed AS output
    INNER JOIN method ON method.id = output.method_id
    INNER JOIN instance ON instance.id = output.instance_id
    INNER JOIN dataset ON dataset.id = instance.dataset_id
    INNER JOIN assignment ON assignment.id = output.assignment_id
    WHERE (:run_id IS NULL or output.run_id = :run_id)
    -- AND method.name NOT IN ('dd-ls0', 'dd-ls1', 'dd-ls2', 'dd-ls3', 'dd-ls4', 'fm', 'fm-bca', 'mp', 'mp-mcf', 'mp-fw', 'fw')
    ORDER BY instance.id
'''

SQL_COUNT = 'SELECT COUNT(*)' + SQL[SQL.find(' FROM '):]


def init_subparser(subparsers):
    parser = subparsers.add_parser('verify-assignments')
    parser.add_argument('--run', '-r')
    parser.add_argument('--model-directory', '-d', required=True)
    return parser


def preprocess_assignment(model, assignment):
    return [a if a >= 0 and a < model.no_right else None for a in assignment[:model.no_left]]


def worker_main(args, in_queue):
    import mpopt.qap
    import mpopt.utils

    old_filename = None
    while True:
        row = in_queue.get()
        if row is None:
            break

        filename = f'{args.model_directory}/{row["dataset"]}/{row["instance"]}.dd.xz'
        if filename != old_filename:
            with mpopt.utils.smart_open(filename, 'rt') as f:
                model = mpopt.qap.parse_dd_model(f)
            old_filename = filename

        assignment = preprocess_assignment(model, json.loads(row['assignment']))
        primals = mpopt.qap.Primals(model, assignment)
        assert primals.check_consistency()

        if abs(row['value'] - primals.evaluate()) > 1e-1:
            print(row, primals.evaluate(), file=sys.stderr)

    print('Terminating')


def execute(args):
    import mpopt.qap
    import mpopt.utils

    with gmbench.db.connect() as db:
        with db:
            cur = db.execute(SQL_COUNT, {'run_id': args.run})
            total = cur.fetchone()[0]

            cur = db.execute(SQL, {'run_id': args.run})

            # We can not use Pool.imap_unordered, because the Pool would consume
            # the iterator in a separate thread. However, the sqlite database
            # must only be used from the thread where it was created. Therefore,
            # we use our own Queue here.
            in_queue = multiprocessing.Queue(100)
            with multiprocessing.Pool(None, worker_main, (args, in_queue)) as pool:
                tick = time.monotonic()
                for i, row in enumerate(cur):
                    in_queue.put(dict(row))

                    if time.monotonic() - tick > 60:
                        print(f'Progress: {i} / {total} ({i / total * 100:.2f}%)')
                        tick = time.monotonic()

                for i in range(pool._processes):
                    in_queue.put(None)

                in_queue.close()
                in_queue.join_thread()

                pool.close()
                pool.join()
