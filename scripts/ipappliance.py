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
import argparse
import inspect
import json
import sys
import time
from datetime import datetime
from threading import Lock, Thread
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


def call_appliance(order, result_dict, ip_address, action, args, kwargs):
    # Given a provider class, find the named method and call it with
    # *args. This could possibly be generalized for other CLI tools.
    appliance = IPAppliance(ip_address)
    result = None

    try:
        call = getattr(appliance, action)
    except AttributeError:
        raise Exception('Action "{}" not found'.format(action))
    if isinstance(getattr(type(appliance), action), property):
        result = call
    else:
        try:
            argspec = inspect.getargspec(call)
        except TypeError:
            try:
                result = call(*args, **kwargs)
            except Exception as e:
                result = e
        else:
            if argspec.keywords is not None or 'log_callback' in argspec.args:
                kwargs['log_callback'] = generate_log_callback(ip_address)
            try:
                result = call(*args, **kwargs)
            except Exception as e:
                result = e
    with lock:
        result_dict[order] = result


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
    results = {}
    threads = []
    log_callback('Calling {}({}, {}) on {}'.format(
        args.action_name,
        ", ".join(map(repr, action_args)),
        ", ".join("{}={}".format(k, repr(v)) for k, v in action_kwargs.iteritems()),
        ", ".join(args.appliances)))
    for order, appliance in enumerate(args.appliances):
        log_callback("=== Starting on {} as thread {}".format(appliance, order))
        thread = Thread(target=call_appliance,
            args=(order, results, appliance, args.action_name, action_args, action_kwargs))
        # Mark as daemon thread for easy-mode KeyboardInterrupt handling
        thread.daemon = True
        threads.append(thread)
        thread.start()

    finished_threads = set()
    while len(finished_threads) < len(threads):
        time.sleep(0.25)
        for order, thread in enumerate(threads):
            if order in finished_threads:
                continue
            thread.join(timeout=0.5)
            if not thread.is_alive():
                finished_threads.add(order)
                log_callback("=== Thread {} finished.".format(order))
                finished_count = float(len(finished_threads))
                total_count = float(len(threads))
                log_callback(
                    "=== Progress: {0:.2f}%".format(100.0 * (finished_count / total_count)))

    results = results.items()
    results.sort(key=lambda pair: pair[0])
    results = [pair[1] for pair in results]

    log_callback("Ended. Result printout follows:")
    rc = 0
    for result in results:
        if isinstance(result, Exception):
            print('Exception {}: {}'.format(type(result).__name__, str(result)))
            rc = 1
        else:
            print(result)
    return rc


if __name__ == '__main__':
    exit(main(parse_args()))
