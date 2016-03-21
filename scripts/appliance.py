#!/usr/bin/env python2
"""
Given the name of a provider from cfme_data and an appliance vm name, call the
corresponding action on that appliance, along with any additional action arguments.

See utils.appliance.Appliance for documentation on the callable methods themselves.

Example usage:

    scripts/appliance.py providername vmname rename "New Name"

Note that attempts to be clever will likely be successful, but fruitless.
For example, this will work but not do anyhting helpful:

    scripts/appliance.py providername vmname __init__

"""
import argparse
import sys

from utils.appliance import Appliance


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('provider_name',
        help='provider name in cfme_data')
    parser.add_argument('vm_name',
        help='appliance vm name')
    parser.add_argument('action',
        help='action to take')
    parser.add_argument('action_args', nargs='*',
        help='positional args to pass to the action function')

    args = parser.parse_args()
    try:
        result = call_appliance(args.provider_name, args.vm_name, args.action, *args.action_args)
        if isinstance(result, list):
            exit = 0
            for entry in result:
                print(entry)
        elif isinstance(result, (basestring, int)):
            exit = 0
            print(result)
        elif isinstance(result, bool):
            # 'True' result becomes flipped exit 0, and vice versa for False
            exit = int(not result)
        elif result is None:
            exit = 0
        else:
            # Unknown type, explode
            raise Exception('Unknown return type for "{}"'.format(args.action))
    except Exception as e:
        exit = 1
        exc_type = type(e).__name__
        if e.message:
            sys.stderr.write('{}: {}\n'.format(exc_type, e.message))
        else:
            sys.stderr.write('{}\n'.format(exc_type))

    return exit


def process_arg(arg):
    """Parse either number or a well-known values. Otherwise pass through."""
    try:
        return int(arg)
    except ValueError:
        pass
    if arg == "True":
        return True
    elif arg == "False":
        return False
    elif arg == "None":
        return None
    else:
        return arg


def process_args(args):
    """We need to pass more than just strings."""
    return map(process_arg, args)


def call_appliance(provider_name, vm_name, action, *args):
    # Given a provider class, find the named method and call it with
    # *args. This could possibly be generalized for other CLI tools.
    appliance = Appliance(provider_name, vm_name)

    try:
        call = getattr(appliance, action)
    except AttributeError:
        raise Exception('Action "{}" not found'.format(action))
    if isinstance(getattr(type(appliance), action), property):
        return call
    else:
        return call(*process_args(args))

if __name__ == '__main__':
    sys.exit(main())
