#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import json
import os
import sys
from utils.conf import env
from utils.sprout import SproutClient


def main():
    host = env.get("sprout", {}).get("hostname", "localhost")
    port = env.get("sprout", {}).get("port", 8000)

    command_args = sys.argv[1:]

    try:
        method = command_args.pop(0)
    except IndexError:
        raise Exception("You have to specify the method!")

    args = []
    while command_args and "=" not in command_args[0] and ":" not in command_args[0]:
        value = command_args.pop(0)
        try:
            value = int(value)
        except ValueError:
            pass
        args.append(value)

    kwargs = {}
    while command_args and "=" in command_args[0] and ":" not in command_args[0]:
        param, value = command_args.pop(0).split("=", 1)
        try:
            value = int(value)
        except ValueError:
            pass
        kwargs[param] = value
    additional_kwargs = {}
    if command_args and ":" in command_args[0]:
        additional_kwargs["auth"] = [x.strip() for x in command_args[0].split(":", 1)]
    elif "SPROUT_USER" in os.environ and "SPROUT_PASSWORD" in os.environ:
        additional_kwargs["auth"] = os.environ["SPROUT_USER"], os.environ["SPROUT_PASSWORD"]
    elif "SPROUT_PASSWORD" in os.environ:
        additional_kwargs["auth"] = os.environ["USER"], os.environ["SPROUT_PASSWORD"]
    client = SproutClient(host=host, port=port, **additional_kwargs)
    print(json.dumps(client.call_method(method, *args, **kwargs)))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("{} {}".format(e.__class__.__name__, "-", str(e)))
        exit(1)
