#!/usr/bin/env python
"""Template tester script, used to test and mark template as usable.

get:
    Export bash vars to be eval'd for template testing with the jenkins runner

latest:
    Export bash vars to be eval'd for getting the latest usable template

mark:
    Mark a template as tested and, if it passes, usable.

"""
import sys

from utils import trackerbot


def get(api):
    try:
        template, provider_key, stream = trackerbot.templates_to_test(api, limit=1)[0]
    except TypeError:
        # No untested providertemplates, all is well
        return 0
    # Let other exceptions be raised.

    # Print envvar exports to be eval'd
    export(
        appliance_template=template,
        provider_key=provider_key,
        stream=stream
    )


def latest(api, stream):
    try:
        res = api.group(stream).get()
    except IndexError:
        # No templates in stream
        return 1

    export(
        appliance_template=res['latest_template'],
        provider_keys=' '.join(res['latest_template_providers'])
    )


def export(**env_vars):
    for varname, value in env_vars.items():
        print 'export %s="%s"' % (varname, value)


def mark(api, provider_key, template, usable):
    trackerbot.mark_provider_template(api, provider_key, template, tested=True, usable=usable)


if __name__ == '__main__':
    parser = trackerbot.cmdline_parser()
    subs = parser.add_subparsers(title='commands', dest='command')

    parse_get = subs.add_parser('get', help='get a template to test')
    parse_get.set_defaults(func=get)

    parse_latest = subs.add_parser('latest', help='get the latest usable template for a provider')
    parse_latest.set_defaults(func=latest)
    parse_latest.add_argument('stream', help='template stream (e.g. upstream, downstream-52z')

    parse_mark = subs.add_parser('mark', help='mark a tested template')
    parse_mark.set_defaults(func=mark)
    parse_mark.add_argument('provider_key')
    parse_mark.add_argument('template')
    parse_mark.add_argument('-n', '--not-usable', dest='usable', action='store_false',
        default=True, help='mark template as not usable (templates are marked usable by default')

    args = parser.parse_args()
    api = trackerbot.api(args.trackerbot_url)
    func_map = {
        get: lambda: get(api),
        latest: lambda: latest(api, args.stream),
        mark: lambda: mark(api, args.provider_key, args.template, args.usable)
    }
    sys.exit(func_map[args.func]())
