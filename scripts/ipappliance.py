#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Invoke actions on appliance(s) given their IPs

See :py:class:`utils.appliance.IPAppliance` for documentation on the callable methods themselves.

Example usage:

    ``scripts/ipappliance.py action_name --args '[1,2,3]' --kwargs '{"a": 1}' 1.2.3.4 2.3.4.5``

``--args`` and ``--kwargs`` are optional.

Returns the resulting value of the call written to the stdout, one line per appliance.

Logs its actions to stderr.

"""
from __future__ import print_function
import argparse
import inspect
import json
import sys
from datetime import datetime
from threading import Lock
from concurrent import futures
import traceback
from utils.appliance import IPAppliance

lock = Lock()


def generate_log_callback(ip):
    def log_callback(s):
        with lock:
            sys.stderr.write(
                "[{}][{}] {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, s))
    return log_callback


def log_callback(s):
    with lock:
        sys.stderr.write(
            "[{}] {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), s))


def call_appliance(ip_address, action, args, kwargs):
    # Given a provider class, find the named method and call it with
    # *args. This could possibly be generalized for other CLI tools.
    appliance = IPAppliance(ip_address)

    try:
        call = getattr(appliance, action)
    except AttributeError:
        raise Exception('Action "{}" not found'.format(action))
    if isinstance(getattr(type(appliance), action), property):
        return call
    else:
        try:
            argspec = inspect.getargspec(call)
        except TypeError:
            return call(*args, **kwargs)
        else:
            if argspec.keywords is not None or 'log_callback' in argspec.args:
                kwargs['log_callback'] = generate_log_callback(ip_address)
            return call(*args, **kwargs)


def parse_args():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action_name',
        help='Name of the action as a method or property of IPAppliance')
    parser.add_argument('--args',
        help='JSON encoded args for action. Must be a list', default=json.dumps([]))
    parser.add_argument('--kwargs',
        help='JSON encoded kwargs for action. Must be a dict', default=json.dumps({}))
    parser.add_argument('appliances', nargs='+',
        help='Appliance IPs to invoke this on')

    return parser.parse_args()


def main(args):
    action_args = json.loads(args.args)
    action_kwargs = json.loads(args.kwargs)
    appliance_calls = {}
    finished_call_futures = []
    log_callback('Calling {}({}, {}) on {}'.format(
        args.action_name,
        ", ".join(map(repr, action_args)),
        ", ".join("{}={}".format(k, repr(v)) for k, v in action_kwargs.iteritems()),
        ", ".join(args.appliances)))

    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        appliance_calls = {executor.submit(call_appliance,
                                           appliance,
                                           args.action_name,
                                           action_args,
                                           action_kwargs): appliance
                           for appliance in args.appliances}

        total_count = len(appliance_calls)
        finished_call_futures = []
        for arrivial_order, future in enumerate(futures.as_completed(appliance_calls)):
            log_callback("=== Progress: {:.2f}% out of {} appliances finished the call".format(
                100.0 * (arrivial_order / total_count),
                total_count))
            finished_call_futures.append(future)

    log_callback("Ended. Result printout follows:")
    rc = 0
    for future in finished_call_futures:  # Note that they are in the order of their arrivial.
        try:
            print(future.result())
        except Exception as exc:
            print("The call on the appliance {} failed: {}".format(
                  appliance_calls[future], exc))
            traceback.print_exc()
            rc = 1
    return rc


if __name__ == '__main__':
    exit(main(parse_args()))
