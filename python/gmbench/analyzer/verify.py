# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import sys

import gmbench.db
import gmbench.verification


def init_subparser(subparsers):
    parser = subparsers.add_parser('verify')
    parser.add_argument('--run', '-r')
    return parser


def execute(args):
    with gmbench.db.connect() as db:
        with db:
            ok, errors = gmbench.verification.missing_instance_in_run(db, args.run)
            if not ok:
                print('The following instances are missing entirely:')
                for error in errors:
                    run = error['run_id']
                    instance = error['instance']
                    print(f'  - run: {run} / instance: {instance}')

            ok, errors = gmbench.verification.missing_method_in_run(db, args.run)
            if not ok:
                print('The following methods are missing entirely:')
                for error in errors:
                    run = error['run_id']
                    method = error['method']
                    print(f'  - run: {run} / method: {method}')

            ok, errors = gmbench.verification.missing_output_in_run(db, args.run)
            if not ok:
                print('The following method/instance combination did never produce any valid datapoint:')
                for error in errors:
                    run = error['run_id']
                    method = error['method']
                    instance = error['instance']
                    print(f'  - run: {run} / method: {method} / instance: {instance}')

            ok, errors = gmbench.verification.missing_trial_in_run(db, args.run)
            if not ok:
                print('For the following method/instance combination only some trials returned any valid datapoint:')
                for error in errors:
                    run = error['run_id']
                    method = error['method']
                    instance = error['instance']
                    count = error['count']
                    total = error['total']
                    print(f'  - run: {run} / method: {method} / instance: {instance} / trials: {count} of {total}')

            ok, errors = gmbench.verification.invalid_value_or_bound(db, args.run)
            if not ok:
                print('For the following instances value/bounds conflicts have been detected:')
                for error in errors:
                    run = error['run_id']
                    instance = error['instance']
                    value_min = error['value_min']
                    bound_max = error['bound_max']
                    print(f'  - run: {run} / instance: {instance} / value_min: {value_min} / bound_max: {bound_max}')

            ok, errors = gmbench.verification.invalid_optima(db, args.run)
            if not ok:
                print('The following optima seem to be invalid (some methods return better value):')
                for error in errors:
                    run = error['run_id']
                    instance = error['instance']
                    optimum = error['optimum']
                    value = error['value_min']
                    print(f'  - run: {run} / instance: {instance} / optimum: {optimum} / value: {value}')

            ok, errors = gmbench.verification.nondeterminism_value(db, args.run)
            if not ok:
                print('The following methods were nondeterministic in different trials:')
                for error in errors:
                    run = error['run_id']
                    method = error['method']
                    instance = error['instance']
                    print(f'  - run: {run} / method: {method} / instance: {instance}')

            ok, errors = gmbench.verification.nondeterminism_time(db, args.run)
            if not ok:
                print('The run times for the following methods differ significantly between trials:')
                for error in errors:
                    run = error['run_id']
                    method = error['method']
                    instance = error['instance']
                    time_diff_max = error['time_diff_max']
                    print(f'  - run: {run} / method: {method} / instance: {instance} / diff: {time_diff_max}')
