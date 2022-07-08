# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

def _first_row_helper(cursor):
    first_row = cursor.fetchone()

    def gen():
        yield first_row
        for row in cursor:
            yield row

    if first_row:
        return False, gen()
    else:
        return True, None


def _generic_missing_helper(db, table, run_id=None):
    has_run_id = run_id is not None
    where = 'WHERE run_id = ?' if has_run_id else ''
    query = f'SELECT * FROM {table} {where}'

    cur = db.execute(query, (run_id,) if has_run_id else ())
    return _first_row_helper(cur)


def missing_instance_in_run(db, run_id=None):
    return _generic_missing_helper(db, 'verification_missing_instance_in_run', run_id)


def missing_method_in_run(db, run_id=None):
    return _generic_missing_helper(db, 'verification_missing_method_in_run', run_id)


def missing_trial_in_run(db, run_id=None):
    return _generic_missing_helper(db, 'verification_missing_trial_in_run', run_id)


def missing_output_in_run(db, run_id=None):
    return _generic_missing_helper(db, 'verification_missing_output_in_run', run_id)


def invalid_value_or_bound(db, run_id=None):
    return _generic_missing_helper(db, 'verification_invalid_value_or_bound', run_id)


def invalid_optima(db, run_id=None):
    return _generic_missing_helper(db, 'verification_invalid_optima', run_id)


def nondeterminism_value(db, run_id=None):
    has_run_id = run_id is not None
    where = 'AND run_id = ?' if has_run_id else ''
    query = f'SELECT * FROM verification_nondeterminism WHERE value_diff_max > 0 {where}'

    cur = db.execute(query, (run_id,) if has_run_id else ())
    return _first_row_helper(cur)


def nondeterminism_time(db, run_id=None):
    has_run_id = run_id is not None
    where = 'AND run_id = ?' if has_run_id else ''
    query = f'SELECT * FROM verification_nondeterminism WHERE time_diff_max > 10 {where}'

    cur = db.execute(query, (run_id,) if has_run_id else ())
    return _first_row_helper(cur)
