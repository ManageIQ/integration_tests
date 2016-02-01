#!/usr/bin/env python
"""Template tester script, used to test and mark template as usable.

get:
    Export bash vars to be eval'd for template testing with the jenkins runner

latest:
    Export bash vars to be eval'd for getting the latest usable template

mark:
    Mark a template as tested and, if it passes, usable.

"""
import os
import sys

from utils import trackerbot


def get(api, request_type=None):
    try:
        template, provider_key, stream, provider_type =\
            trackerbot.templates_to_test(api, request_type=request_type, limit=1)[0]
    except (IndexError, TypeError):
        # No untested provider templates, all is well
        return 0

    # Print envvar exports to be eval'd
    export(
        appliance_template=template,
        provider_key=provider_key,
        stream=stream,
        provider_type=provider_type
    )


def latest(api, stream, provider_key=None):
    try:
        if provider_key:
            prov = api.provider(provider_key).get()
            res = prov['latest_templates'][stream]
        else:
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
        print 'export %s="%s";' % (varname, value)
    print "# to import these into your bash environment: eval $(%s)" % ' '.join(sys.argv)


def mark(api, provider_key, template, usable, diagnose):
    # set some defaults
    diagnosis = None
    build_number = None
    if not usable:
        build_number = os.environ.get('BUILD_NUMBER', None)

#   temporarily disabled; diagnosis is causing template marking to fail on downstream appliances :(
#         if diagnose:
#             # diagnose will return None on a usable appliance, so don't bother
#             from utils.appliance import IPAppliance
#             ipa = IPAppliance()
#             diagnosis = ipa.diagnose_evm_failure()
#             if diagnosis:
#                 logger.error('Appliance failed: {}'.format(diagnosis.split(os.linesep)[0]))

    trackerbot.mark_provider_template(api, provider_key, template, tested=True, usable=usable,
        diagnosis=diagnosis, build_number=build_number)


def retest(api, provider_key, template):
    trackerbot.mark_provider_template(api, provider_key, template, tested=False)

if __name__ == '__main__':
    parser = trackerbot.cmdline_parser()
    subs = parser.add_subparsers(title='commands', dest='command')

    parse_get = subs.add_parser('get', help='get a template to test')
    parse_get.set_defaults(func=get)
    parse_get.add_argument('--request_type', dest='request_type',
                           help='get a teamplate based on provider type')

    parse_latest = subs.add_parser('latest', help='get the latest usable template for a provider')
    parse_latest.set_defaults(func=latest)
    parse_latest.add_argument('stream', help='template stream (e.g. upstream, downstream-52z')
    parse_latest.add_argument('provider_key', nargs='?', default=None)

    parse_mark = subs.add_parser('mark', help='mark a tested template')
    parse_mark.set_defaults(func=mark)
    parse_mark.add_argument('provider_key')
    parse_mark.add_argument('template')
    parse_mark.add_argument('-n', '--not-usable', dest='usable', action='store_false',
        default=True, help='mark template as not usable (templates are marked usable by default')
    parse_mark.add_argument('-d', '--diagnose', dest='diagnose', action='store_true',
        default=False, help='attempt to diagnose an unusable template and submit the result')

    parse_retest = subs.add_parser('retest', help='flag a tested template for retesting')
    parse_retest.set_defaults(func=retest)
    parse_retest.add_argument('provider_key')
    parse_retest.add_argument('template')

    args = parser.parse_args()
    api = trackerbot.api(args.trackerbot_url)
    func_map = {
        get: lambda: get(api, args.request_type),
        latest: lambda: latest(api, args.stream, args.provider_key),
        mark: lambda: mark(api, args.provider_key, args.template, args.usable, args.diagnose),
        retest: lambda: retest(api, args.provider_key, args.template),
    }
    sys.exit(func_map[args.func]())
