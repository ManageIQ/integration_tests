#!/usr/bin/env python2

import argparse
import datetime
import re
import sys
from contextlib import closing
from jinja2 import Environment, FileSystemLoader
from urllib2 import urlopen, HTTPError

from utils import trackerbot
from utils.path import template_path, log_path
from utils.wait import wait_for

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
    parser.add_argument("--template", dest="appliance_template",
                        help="appliance/latest template name",
                        default=None)
    parser.add_argument("--output", dest="output", help="target file name",
                        default=log_path.join('template_tester_results.log').strpath)
    args = parser.parse_args()
    return args


def get_latest_tested_template_on_stream(api, template_stream_name):
    stream = {}
    try:
        print("wait until all the provider images are uploaded to latest directory")
        wait_for(templates_uploaded,
                 [api, template_stream_name], fail_condition=False, delay=5, timeout='1h')
    except Exception as e:
        print(e)
        print("less than three provider images are uploaded to latest directory")

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


def images_uploaded(stream):
    if 'upstream' in stream:
        stream = 'upstream'
    elif '55z' in stream:
        stream = 'downstream_55'
    elif '54z' in stream:
        stream = 'downstream_54'
    dir_url = \
        'http://file.cloudforms.lab.eng.rdu2.redhat.com/builds/cfme/' + stream + '/latest/'
    name_dict = {}
    try:
        with closing(urlopen(dir_url)) as urlpath:
            string_from_url = urlpath.read()
    except HTTPError as e:
        print(str(e))
        return None

    rhevm_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhevm|ovirt)[^"\'>]*)')
    rhevm_image_name = rhevm_pattern.findall(string_from_url)
    rhos_pattern = re.compile(r'<a href="?\'?([^"\']*(?:rhos|openstack|rhelosp)[^"\'>]*)')
    rhos_image_name = rhos_pattern.findall(string_from_url)
    scvmm_pattern = re.compile(r'<a href="?\'?([^"\']*hyperv[^"\'>]*)')
    scvmm_image_name = scvmm_pattern.findall(string_from_url)
    vsphere_pattern = re.compile(r'<a href="?\'?([^"\']*vsphere[^"\'>]*)')
    vsphere_image_name = vsphere_pattern.findall(string_from_url)

    if len(rhevm_image_name) is not 0:
        name_dict['template_rhevm'] = rhevm_image_name[0]
    if len(rhos_image_name) is not 0:
        name_dict['template_rhos'] = rhos_image_name[0]
    if len(scvmm_image_name) is not 0:
        name_dict['template_scvmm'] = scvmm_image_name[0]
    if len(vsphere_image_name) is not 0:
        name_dict['template_vsphere'] = vsphere_image_name[0]

    return name_dict


def templates_uploaded(api, stream):
    if len(images_uploaded(stream)) > 2:
        for temp in api.template.get(
                limit=1, tested=False, group__name=stream).get('objects', []):
            if not filter(lambda x: 'rhos' in x, temp['providers']):
                return False
            if not filter(lambda x: 'rhevm' in x, temp['providers']):
                return False
            if not filter(lambda x: 'vsphere' in x, temp['providers']):
                return False
        return True
    return False


def get_untested_templates(api, stream_group):
    return api.untestedtemplate.get(template__group__name=stream_group).get('objects', [])


def generate_html_report(api, stream, filename, appliance_template):

    number_of_images_before = len(images_uploaded(stream))
    stream_data = get_latest_tested_template_on_stream(api, stream)

    if len(images_uploaded(stream)) > number_of_images_before:
        print("new images are uploaded, new Jenkins job will generate the report")
        sys.exit()
    elif appliance_template and appliance_template != stream_data['template_name']:
        print("the report will be generated only for the latest templates")
        sys.exit()

    if stream_data and not get_untested_templates(api, stream_data['group_name']):
        print("Found tested template for {}".format(stream))
        print("Gathering tested template data for {}".format(stream))
        stream_html = [stream_data['template_name'], stream_data['passed_on_providers'],
                       stream_data['failed_on_providers'], stream_data['group_name'],
                       stream_data['datestamp']]
        if 'html' in filename:
            data = template_env.get_template('template_tester_report.html').render(
                upstream=stream_html)
            with open(filename, 'w') as report:
                report.write(data)
        else:
            with open(filename, 'a+') as report:

                if 'template_rhos' not in images_uploaded(stream):
                    report.write('\nMISSING: Image for OpenStack')
                elif filter(lambda x: 'rhos' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(images_uploaded(stream)['template_rhos']))
                    map(lambda(x): report.write('\n{}: Passed'.format(x)) if 'rhos' in x else '',
                        stream_data['passed_on_providers'])
                else:
                    report.write('\n\nFAILED: {}'.format(images_uploaded(stream)['template_rhos']))
                    map(lambda(x): report.write('\n{}: Failed'.format(x)) if 'rhos' in x else '',
                        stream_data['failed_on_providers'])

                if 'template_rhevm' not in images_uploaded(stream):
                    report.write('\nMISSING: Image for RHEVM')
                elif filter(lambda x: 'rhevm' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(
                        images_uploaded(stream)['template_rhevm']))
                    map(lambda(x): report.write('\n{}: Passed'.format(x)) if 'rhevm' in x else '',
                        stream_data['passed_on_providers'])
                else:
                    report.write('\n\nFAILED: {}'.format(
                        images_uploaded(stream)['template_rhevm']))
                    map(lambda(x): report.write('\n{}: Failed'.format(x)) if 'rhevm' in x else '',
                        stream_data['failed_on_providers'])

                if 'template_vsphere' not in images_uploaded(stream):
                    report.write('\nMISSING: Image for VIRTUALCENTER')
                elif filter(lambda x: 'vsphere' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(
                        images_uploaded(stream)['template_vsphere']))
                    map(lambda(x): report.write('\n{}: Passed'.format(x)) if 'vsphere' in x else '',
                        stream_data['passed_on_providers'])
                else:
                    report.write('\n\nFAILED: {}'.format(
                        images_uploaded(stream)['template_vsphere']))
                    map(lambda(x): report.write('\n{}: Failed'.format(x)) if 'vsphere' in x else '',
                        stream_data['failed_on_providers'])
        print("template_tester_results report generated")
    else:
        print("No Templates tested on: {}".format(datetime.datetime.now()))


if __name__ == '__main__':
    args = parse_cmd_line()
    api = trackerbot.api(args.trackerbot_url)
    if not args.stream:
        sys.exit("stream cannot be None, specify the stream as --stream <stream-name> ")
    generate_html_report(api, args.stream, args.output, args.appliance_template)
