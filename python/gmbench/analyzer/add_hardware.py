# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import sys

import gmbench.db


def init_subparser(subparsers):
    parser = subparsers.add_parser('add-hardware')
    parser.add_argument('--name', '-n', required=True)
    parser.add_argument('--description', '-d')
    return parser


def execute(args):
    if not args.description:
        print('No descrption provided, going to read description from stdin.')
        args.description = sys.stdin.read().rstrip()

    with gmbench.db.connect() as db:
        with db:
            db.execute('INSERT OR REPLACE INTO hardware (name, description) '
                       'VALUES                          (   ?,           ?)',
                       (args.name, args.description))
