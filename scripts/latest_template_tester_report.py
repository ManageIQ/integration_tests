#!/usr/bin/env python2

import argparse
import datetime
import sys
from jinja2 import Environment, FileSystemLoader

from utils import trackerbot
from utils.path import template_path, log_path

template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument("--tracketbot-url", dest="trackerbot_url",
                        help="tracker bot url to make api call",
                        default='http://10.16.4.32/trackerbot/api')
    parser.add_argument("--stream", dest="stream",
                        help="stream to generate the template test result")
    parser.add_argument("--output", dest="output", help="target file name",
                        default=log_path.join('template_tester_results.html').strpath)
    args = parser.parse_args()
    return args


def get_latest_tested_template_on_stream(api, template_stream_name):
    stream = {}
    for temp in api.template.get(
            limit=1, tested=True, group__name=template_stream_name).get('objects', []):
        stream['template_name'] = temp['name']
        passed_on_providers = []
        failed_on_providers = []
        usable_providers = temp['usable_providers']
        all_providers = temp['providers']
        if len(usable_providers) == len(all_providers):
            passed_on_providers = all_providers
        elif not usable_providers:
            failed_on_providers = all_providers
        else:
            passed_on_providers = usable_providers
            failed_on_providers = list(set(all_providers) - set(usable_providers))
        stream['passed_on_providers'] = passed_on_providers
        stream['failed_on_providers'] = failed_on_providers
        stream['group_name'] = temp['group']['name']
        stream['datestamp'] = temp['datestamp']
    return stream


def get_untested_templates(api, stream_group):
        return api.untestedtemplate.get(template__group__name=stream_group).get('objects', [])


def generate_html_report(api, stream, filename):

    stream_data = get_latest_tested_template_on_stream(api, stream)
    if stream_data and not get_untested_templates(api, stream_data['group_name']):
        print("Found tested template for {}".format(stream))
        print("Gathering tested template data for {}".format(stream))
        stream_html = [stream_data['template_name'], stream_data['passed_on_providers'],
                       stream_data['failed_on_providers'], stream_data['group_name'],
                       stream_data['datestamp']]
        data = template_env.get_template('template_tester_report.html').render(
            upstream=stream_html)
        with open(filename, 'w') as report:
            report.write(data)
        print("html file template_tester_results_test.html generated")
    else:
        print("No Templates tested on: {}".format(datetime.datetime.now()))


if __name__ == '__main__':
    args = parse_cmd_line()
    api = trackerbot.api(args.trackerbot_url)
    if not args.stream:
        sys.exit("stream cannot be None, specify the stream as --stream <stream-name> ")
    generate_html_report(api, args.stream, args.output)
