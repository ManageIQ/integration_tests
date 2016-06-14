#!/usr/bin/env python2

import argparse
import datetime
import re
import sys
from contextlib import closing
from jinja2 import Environment, FileSystemLoader
from urllib2 import urlopen, HTTPError

from utils import trackerbot
from utils.conf import credentials
from utils.conf import cfme_data
from utils.path import template_path, log_path
from utils.ssh import SSHClient
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
                        help="appliance/latest template name")
    parser.add_argument("--provider", dest="provider",
                        help="provider under test")
    parser.add_argument("--output", dest="output", help="target file name",
                        default=log_path.join('template_tester_results.log').strpath)
    args = parser.parse_args()
    return args


def make_ssh_client(rhevip, sshname, sshpass):
    connect_kwargs = {
        'username': sshname,
        'password': sshpass,
        'hostname': rhevip
    }
    return SSHClient(**connect_kwargs)


def get_latest_tested_template_on_stream(api, template_stream_name, template_name):
    stream = {}
    try:
        wait_for_images_on_web_repo(template_stream_name, template_name)
        wait_for_templates_on_providers(api, template_stream_name, template_name)
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
    """Checks for the uploaded build images at the latest directory.
       the stream name in the weburl for latest directory is formatted
       differently on trackerbot. This method formats the 'stream' before
       browsing the web url.
    Args:
        stream: stream name in trackerbot stream name format
                e.g. downstream-55z, downstream-nightly, upstream etc..
    returns: dictionary with key/value 'provider type and image names uploaded'.
    """
    dir_url = cfme_data['basic_info']['cfme_images_url'][stream]
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


def all_images_uploaded(stream, template=None):
    if get_untested_templates(api, stream, template):
        print('report will not be generated, proceed with the next untested provider')
        sys.exit()
    if 'template_rhevm' not in images_uploaded(stream):
        return False
    if 'template_rhos' not in images_uploaded(stream):
        return False
    if 'template_vsphere' not in images_uploaded(stream):
        return False
    if 'template_scvmm' not in images_uploaded(stream):
        return False
    return True


def wait_for_images_on_web_repo(stream, template):
    try:
        print('wait for images upload to latest directory')
        wait_for(all_images_uploaded, [stream, template],
                 fail_condition=False, delay=5, timeout='30m')
        return True
    except Exception as e:
        print(e)
        return False


def templates_uploaded_on_providers(api, stream, template):
    if get_untested_templates(api, stream, template):
        print('report will not be generated, proceed with the next untested provider')
        sys.exit()
    for temp in api.template.get(
            limit=1, tested=False, group__name=stream).get('objects', []):
        if 'template_rhevm' in images_uploaded(stream):
            if not filter(lambda x: 'rhevm' in x, temp['providers']):
                return False
        if 'template_rhos' in images_uploaded(stream):
            if not filter(lambda x: 'rhos' in x, temp['providers']):
                return False
        if 'template_vsphere' in images_uploaded(stream):
            if not filter(lambda x: 'vsphere' in x, temp['providers']):
                return False
        if 'template_scvmm' in images_uploaded(stream):
            if not filter(lambda x: 'scvmm' in x, temp['providers']):
                return False
    return True


def wait_for_templates_on_providers(api, stream, template):
    try:
        print('wait for templates upload to providers')
        wait_for(templates_uploaded_on_providers,
                 [api, stream, template], fail_condition=False, delay=5, timeout='40m')
    except Exception as e:
        print(e)
        return False


def get_untested_templates(api, stream_group, appliance_template=None):
    return api.untestedtemplate.get(
        template__group__name=stream_group, template=appliance_template).get('objects', [])


def update_template_log(appliance_template, action, provider=None, failed_providers=None):
    try:
        trackerbot_ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', args.trackerbot_url)[0]
        creds = credentials['host_default']
        sshclient = make_ssh_client(trackerbot_ip, creds['username'], creds['password'])
        template_resultlog = log_path.join('template_result.log').strpath
        if action == 'create':
            command = 'mkdir -p /home/amavinag/{}'.format(appliance_template)
            sshclient.run_command(command)
            sshclient.put_file(template_resultlog, remote_file='/home/amavinag/{}/{}'.format(
                appliance_template, provider))
        if action == 'merge':
            with open(template_resultlog, 'w') as report:
                command = 'cd /home/amavinag/{}/&&cat {}'.format(appliance_template,
                                                                 ' '.join(failed_providers))
                status, output = sshclient.run_command(command)
                if 'No such file or directory' in output:
                    command = 'cd /home/amavinag/{}/&&cat *'.format(appliance_template)
                    status, output = sshclient.run_command(command)
                report.write(output)
                report.close()
        elif action == 'remove':
            sshclient.run_command('cd /home/amavinag/&&rm -rf {}'.format(
                appliance_template))
        sshclient.close()
    except Exception as e:
        print(e)
        return False


def generate_html_report(api, stream, filename, appliance_template, provider):

    status = 'PASSED'
    number_of_images_before = len(images_uploaded(stream))
    update_template_log(appliance_template, action='create', provider=provider)
    if get_untested_templates(api, stream, appliance_template):
        print('report will not be generated, proceed with the next untested provider')
        sys.exit()
    stream_data = get_latest_tested_template_on_stream(api, stream, appliance_template)

    if len(images_uploaded(stream)) > number_of_images_before:
        print("new images are uploaded on latest directory, wait for upload on providers")
        wait_for_templates_on_providers(api, stream)
    if appliance_template and appliance_template != stream_data['template_name']:
        print("the report will be generated only for the latest templates")
        sys.exit()

    if stream_data and not get_untested_templates(api, stream_data['group_name'],
                                                  appliance_template):
        print("Found tested template for {}".format(stream))
        print("Gathering tested template data for {}".format(stream))
        print("Updating the template log")
        update_template_log(appliance_template, action='merge',
                            failed_providers=stream_data['failed_on_providers'])
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
                    print('\n\nMISSING: Image for OpenStack in latest directory')
                    report.write('\n\nMISSING: Image for OpenStack in latest directory')
                elif filter(lambda x: 'rhos' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(images_uploaded(stream)['template_rhos']))
                    map(lambda(x): report.write('\n{}: Passed'.format(x)) if 'rhos' in x else '',
                        stream_data['passed_on_providers'])
                elif filter(lambda x: 'rhos' in x, stream_data['failed_on_providers']):
                    report.write('\n\nFAILED: {}'.format(images_uploaded(stream)['template_rhos']))
                    map(lambda(x): report.write('\n{}: Failed'.format(x)) if 'rhos' in x else '',
                        stream_data['failed_on_providers'])
                else:
                    print('\n\nMISSING: OpenStack template is not available on any '
                          'rhos providers yet')
                    report.write('\n\nMISSING: OpenStack template is not available on any '
                                 'rhos providers yet')

                if 'template_rhevm' not in images_uploaded(stream):
                    print('\n\nMISSING: Image for RHEVM in latest directory')
                    report.write('\n\nMISSING: Image for RHEVM in latest directory')
                elif filter(lambda x: 'rhevm' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(
                        images_uploaded(stream)['template_rhevm']))
                    map(lambda(x): report.write('\n{}: Passed'.format(x)) if 'rhevm' in x else '',
                        stream_data['passed_on_providers'])
                elif filter(lambda x: 'rhevm' in x, stream_data['failed_on_providers']):
                    report.write('\n\nFAILED: {}'.format(
                        images_uploaded(stream)['template_rhevm']))
                    map(lambda(x): report.write('\n{}: Failed'.format(x)) if 'rhevm' in x else '',
                        stream_data['failed_on_providers'])
                else:
                    print('\n\nMISSING: RHEVM template is not available on any '
                          'rhevm providers yet')
                    report.write('\n\nMISSING: RHEVM template is not available on any '
                                 'rhevm providers yet')

                if 'template_vsphere' not in images_uploaded(stream):
                    print('\n\nMISSING: Image for VIRTUALCENTER in latest directory')
                    report.write('\n\nMISSING: Image for VIRTUALCENTER in latest directory')
                elif filter(lambda x: 'vsphere' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(
                        images_uploaded(stream)['template_vsphere']))
                    map(lambda(x): report.write(
                        '\n{}: Passed'.format(x)) if 'vsphere' in x else '',
                        stream_data['passed_on_providers'])
                elif filter(lambda x: 'vsphere' in x, stream_data['failed_on_providers']):
                    report.write('\n\nFAILED: {}'.format(
                        images_uploaded(stream)['template_vsphere']))
                    map(lambda(x): report.write(
                        '\n{}: Failed'.format(x)) if 'vsphere' in x else '',
                        stream_data['failed_on_providers'])
                else:
                    print('\n\nMISSING: VIRTUALCENTER template is not available on any '
                          'vmware providers yet')
                    report.write('\n\nMISSING: VIRTUALCENTER template is not available on any '
                                 'vmware providers yet')

                if 'template_scvmm' not in images_uploaded(stream):
                    print('\n\nMISSING: Image for SCVMM in latest directory')
                    report.write('\n\nMISSING: Image for SCVMM in latest directory')
                elif filter(lambda x: 'scvmm' in x, stream_data['passed_on_providers']):
                    report.write('\n\nPASSED: {}'.format(
                        images_uploaded(stream)['template_scvmm']))
                    map(lambda(x): report.write(
                        '\n{}: Passed'.format(x)) if 'scvmm' in x else '',
                        stream_data['passed_on_providers'])
                elif filter(lambda x: 'scvmm' in x, stream_data['failed_on_providers']):
                    report.write('\n\nFAILED: {}'.format(
                        images_uploaded(stream)['template_scvmm']))
                    map(lambda(x): report.write(
                        '\n{}: Failed'.format(x)) if 'scvmm' in x else '',
                        stream_data['failed_on_providers'])
                else:
                    print('\n\nMISSING: SCVMM template is not available on any '
                          'scvmm providers yet')
                    report.write('\n\nMISSING: SCVMM template is not available on any '
                                 'scvmm providers yet')
                report.seek(0, 0)
                if "FAILED" in report.read():
                    status = "FAILED"
                report.close()
        update_template_log(appliance_template, action='remove')
        print("template_tester_results report generated:{}".format(status))
    else:
        print("No Templates tested on: {}".format(datetime.datetime.now()))


if __name__ == '__main__':
    args = parse_cmd_line()
    api = trackerbot.api(args.trackerbot_url)
    if not args.stream or not args.appliance_template:
        sys.exit("stream and appliance_template "
                 "cannot be None, specify the stream as --stream <stream-name>"
                 "and template as --template <template-name>")
    generate_html_report(api, args.stream, args.output, args.appliance_template, args.provider)
