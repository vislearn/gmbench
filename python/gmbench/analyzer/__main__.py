# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>

import argparse
import os
import sys

import gmbench.analyzer.add_hardware
import gmbench.analyzer.export
import gmbench.analyzer.generate_table
import gmbench.analyzer.import_benchmark
import gmbench.analyzer.import_datasets
import gmbench.analyzer.init_database
import gmbench.analyzer.plot_cactus
import gmbench.analyzer.plot_perf
import gmbench.analyzer.postprocess
import gmbench.analyzer.remove_slow_trials
import gmbench.analyzer.verify
import gmbench.analyzer.verify_assignments


def main():
    if 'OVERRIDE_ARGV0' in os.environ:
        sys.argv[0] = os.environ['OVERRIDE_ARGV0']
        del os.environ['OVERRIDE_ARGV0']

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    for name, module in sys.modules.items():
        if name.startswith('gmbench.analyzer.'):
            subparser = module.init_subparser(subparsers)
            subparser.set_defaults(module=module)
    args = parser.parse_args()

    if 'module' in args:
        args.module.execute(args)
    else:
        parser.print_usage(sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
