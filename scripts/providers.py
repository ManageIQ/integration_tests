#!/usr/bin/env python2
"""
Given the name of a provider from cfme_data and using credentials from
the credentials stash, call the corresponding action on that provider, along
with any additional action arguments.

See mgmtsystem for documentation on the callable methods themselves.

Example usage:

    scripts/providers.py providername stop_vm vm-name

Note that attempts to be clever will likely be successful, but fruitless.
For example, this will work but not do anyhting helpful:

    scripts/providers.py providername __init__ username password


You can also specify keyword arguments, similarly like the argparse works:

    scripts/providers.py somevsphere do_action 1 2 --foo bar

It expects pairs in format ``--key value``. If you fail to provide such formatted arguments, an
error will happen.

"""
import argparse
import os
import sys
from utils import iterate_pairs, process_shell_output
from utils.providers import get_mgmt

# Make sure the parent dir is on the path before importing get_mgmt
cfme_tests_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, cfme_tests_path)


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider_name',
        help='provider name in cfme_data')
    parser.add_argument('action',
        help='action to take (list_vm, stop_vm, delete_vm, etc.)')
    parser.add_argument('action_args', nargs='*',
        help='foo')

    args, kw_argument_list = parser.parse_known_args()
    kwargs = {}
    for key, value in iterate_pairs(kw_argument_list):
        if not key.startswith('--'):
            raise Exception('Wrong kwargs specified!')
        key = key[2:]
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
        kwargs[key] = value
    try:
        result = call_provider(args.provider_name, args.action, *args.action_args, **kwargs)
        exit, output = process_shell_output(result)
    except Exception as e:
        exit = 1
        exc_type = type(e).__name__
        if str(e):
            sys.stderr.write('{}: {}\n'.format(exc_type, str(e)))
        else:
            sys.stderr.write('{}\n'.format(exc_type))
    else:
        if output is not None:
            print(output)

    return exit


def call_provider(provider_name, action, *args, **kwargs):
    # Given a provider class, find the named method and call it with
    # *args. This could possibly be generalized for other CLI tools.
    provider = get_mgmt(provider_name)

    try:
        call = getattr(provider, action)
    except AttributeError:
        raise Exception('Action {} not found'.format(repr(action)))
    return call(*args, **kwargs)


if __name__ == '__main__':
    sys.exit(main())
