# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import json
import math
import time
import types

import gmbench.db


def init_subparser(subparsers):
    return subparsers.add_parser('postprocess')


def accuracy(assignment, groundtruth, known_nodes_only=True):
    if not groundtruth:
        return None

    if not assignment:
        return 0.0

    #assert len(assignment) == len(groundtruth)
    assert len(assignment) >= len(groundtruth)

    correct, total = 0, 0
    for a, g in zip(assignment, groundtruth):
        if g or not known_nodes_only:
            total += 1

        if g and a in g:
            correct += 1

    return correct / total


def fetch_postprocessed_output(db, progress_handler=None):
    cur = db.execute('SELECT count(*) FROM output')
    total, = cur.fetchone()

    cur = db.execute('SELECT output.id AS output_id, output.run_id, output.method_id, '
                     '       output.instance_id, output.time, output.value, '
                     '       output.bound, assignment.id AS assignment_id, '
                     '       assignment.value AS assignment, instance.groundtruth '
                     'FROM output '
                     'INNER JOIN instance ON instance.id = output.instance_id '
                     'LEFT OUTER JOIN assignment ON assignment.id = output.assignment_id '
                     'ORDER BY output.run_id, output.method_id, '
                     '         output.instance_id, output.time')

    coalesce = lambda a, b: a if a is not None else b

    def new_state():
        state = types.SimpleNamespace()
        state.last_group = None
        state.best_value = math.inf
        state.best_assignment = None
        state.best_assignment_id = None
        state.best_bound = -math.inf
        return state

    state = new_state()

    for i, row in enumerate(cur):
        if progress_handler is not None:
            progress_handler(i, total)

        curr_group = (row['run_id'], row['method_id'], row['instance_id'])
        curr_value = coalesce(row['value'], math.inf)
        curr_bound = coalesce(row['bound'], -math.inf)

        group_changed = curr_group != state.last_group
        if group_changed:
            state = new_state()

        value_improved = curr_value < state.best_value
        bound_improved = curr_bound > state.best_bound

        if value_improved:
            state.best_value = curr_value
            state.best_assignment_id = row['assignment_id']

            if a := row['assignment']:
                state.best_assignment = json.loads(a)
            else:
                state.best_assignment = None

        if bound_improved:
            state.best_bound = curr_bound

        if (group_changed or value_improved or bound_improved):
            groundtruth = row['groundtruth']
            if groundtruth:
                groundtruth = json.loads(groundtruth)

            yield (row['run_id'],
                   row['method_id'],
                   row['instance_id'],
                   row['time'],
                   state.best_value,
                   state.best_bound,
                   state.best_assignment_id,
                   accuracy(state.best_assignment, groundtruth, known_nodes_only=False),
                   accuracy(state.best_assignment, groundtruth, known_nodes_only=True))

        state.last_group = curr_group


def insert_postprocessed_output(db, rows):
    db.executemany('INSERT INTO output_postprocessed ('
                   '    run_id, method_id, instance_id, time, value, bound, '
                   '    assignment_id, accuracy_all_nodes, accuracy_known_nodes) '
                   'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   rows)


def execute(args):
    time_last = time.monotonic()
    def progress_handler(current, total):
        nonlocal time_last
        time_current = time.monotonic()
        if time_current - time_last >= 10:
            print(f'Progress: {current} / {total} rows ({current / total * 100:.2f}%)')
            time_last = time_current

    with gmbench.db.connect() as db:
        with db:
            db.execute('DELETE FROM output_postprocessed')
            rows = fetch_postprocessed_output(db, progress_handler)
            insert_postprocessed_output(db, rows)
            print('Done.')
