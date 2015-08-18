#!/usr/bin/env python2
"""
Given the name of a provider from cfme_data and using credentials from
the credentials stash, call the corresponding action on that provider, along
with any additional action arguments.

See cfme_pages/common/mgmt_system.py for documentation on the callable methods
themselves.

Example usage:

    scripts/providers.py providername stop_vm vm-name

Note that attempts to be clever will likely be successful, but fruitless.
For example, this will work but not do anyhting helpful:

    scripts/providers.py providername __init__ username password

"""
import argparse
import os
import sys

# Make sure the parent dir is on the path before importing get_mgmt
cfme_tests_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, cfme_tests_path)

from utils.providers import get_mgmt


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider_name',
        help='provider name in cfme_data')
    parser.add_argument('action',
        help='action to take (list_vm, stop_vm, delete_vm, etc.)')
    parser.add_argument('action_args', nargs='*',
        help='foo')

    args = parser.parse_args()
    try:
        result = call_provider(args.provider_name, args.action, *args.action_args)
        if isinstance(result, list):
            exit = 0
            for entry in sorted(result):
                print entry
        elif isinstance(result, str):
            exit = 0
            print result
        elif isinstance(result, bool):
            # 'True' result becomes flipped exit 0, and vice versa for False
            exit = int(not result)
        else:
            # Unknown type, print it
            exit = 0
            print str(result)
    except Exception as e:
        exit = 1
        exc_type = type(e).__name__
        if e.message:
            sys.stderr.write('%s: %s\n' % (exc_type, e.message))
        else:
            sys.stderr.write('%s\n' % exc_type)

    return exit


def call_provider(provider_name, action, *args):
    # Given a provider class, find the named method and call it with
    # *args. This could possibly be generalized for other CLI tools.
    provider = get_mgmt(provider_name)

    try:
        call = getattr(provider, action)
    except AttributeError:
        raise Exception('Action "%s" not found' % action)
    return call(*args)

if __name__ == '__main__':
    sys.exit(main())
