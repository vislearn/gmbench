# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import os
import os.path

import gmbench.db


def init_subparser(subparsers):
    return subparsers.add_parser('init-database')


def execute(args):
    if os.path.exists(gmbench.db.DB_FILE):
        print('Database does already exist.')
        user = input('Remove it before it before creating schema? [y/N] ')
        if user.strip().lower() == 'y':
            os.remove(gmbench.db.DB_FILE)

    with gmbench.db.connect(execute_schema=False) as db:
        with db:
            # Delete all views as they can be recreated without data loss.
            cur = db.execute("SELECT name FROM sqlite_master WHERE type='view'")
            for row in cur:
                db.execute(f"DROP VIEW {row['name']}")

            cur.executescript(gmbench.db.DB_SCHEMA)
