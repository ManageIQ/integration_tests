#!/usr/bin/env python3
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

from cfme.utils import trackerbot


def get(api, request_type=None, template_name=None):
    list_of_templates = trackerbot.templates_to_test(api, request_type=request_type, limit=200)

    if len(list_of_templates) == 0:
        # No templates to test for this provider type
        return 0

    if not template_name:
        # If no specific name specified, return 1st element
        template, provider_key, stream, provider_type = list_of_templates[0]
    else:
        # Filter the list for only templates matching 'template_name'
        filtered_list = [t for t in list_of_templates if t[0] == template_name]
        if len(filtered_list) > 0:
            template, provider_key, stream, provider_type = filtered_list[0]
        else:
            # No templates to test for this template name
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
        print('export {}="{}";'.format(varname, value))
    print("# to import these into your bash environment: eval $({})".format(' '.join(sys.argv)))


def mark(api, provider_key, template, usable, diagnose):
    # set some defaults
    diagnosis = None
    build_number = None
    if not usable:
        build_number = os.environ.get('BUILD_NUMBER')

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


def check_tested(api, template_name, provider_type):
    """
    Check if a template has been tested and passed (marked usable) for a provider.

    If not usable, mark it untested so jenkins picks it up for testing.
    """
    trackerbot.mark_unusable_as_untested(api, template_name, provider_type)
    print(str(trackerbot.check_if_tested(api, template_name, provider_type)).lower())


if __name__ == '__main__':
    parser = trackerbot.cmdline_parser()
    subs = parser.add_subparsers(title='commands', dest='command')

    parse_get = subs.add_parser('get', help='get a template to test')
    parse_get.set_defaults(func=get)
    parse_get.add_argument('--request_type', dest='request_type', help='provider type')
    parse_get.add_argument('--template', dest='template', help='template name (optional)')

    parse_check_tested = subs.add_parser(
        'check_tested', help='check if template passed tests at least once on given provider type')
    parse_check_tested.set_defaults(func=check_tested)
    parse_check_tested.add_argument('--request_type', dest='request_type', help='provider type')
    parse_check_tested.add_argument('--template', dest='template', help='template name')

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
        get: lambda: get(api, args.request_type, args.template),
        latest: lambda: latest(api, args.stream, args.provider_key),
        mark: lambda: mark(api, args.provider_key, args.template, args.usable, args.diagnose),
        retest: lambda: retest(api, args.provider_key, args.template),
        check_tested: lambda: check_tested(api, args.template, args.request_type),
    }
    sys.exit(func_map[args.func]())
