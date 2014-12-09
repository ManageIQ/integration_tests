#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys
from utils.conf import cfme_data
from utils.sprout import SproutClient


def main():
    host = cfme_data.get("sprout", {}).get("hostname", "localhost")
    port = cfme_data.get("sprout", {}).get("port", 8000)

    client = SproutClient(host=host, port=port)

    command_args = sys.argv[1:]

    try:
        method = command_args.pop(0)
    except IndexError:
        raise Exception("You have to specify the method!")

    args = []
    while command_args and "=" not in command_args[0]:
        value = command_args.pop(0)
        try:
            value = int(value)
        except ValueError:
            pass
        args.append(value)

    kwargs = {}
    while command_args and "=" in command_args[0]:
        param, value = command_args.pop(0).split("=", 1)
        try:
            value = int(value)
        except ValueError:
            pass
        kwargs[param] = value

    print client.call_method(method, *args, **kwargs)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print str(e)
        exit(1)
