#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import argparse
import jenkins
import re
import requests
import subprocess

from requests.auth import HTTPBasicAuth
from urlparse import urlsplit, urlunsplit

from cfme.utils.appliance import IPAppliance
from cfme.utils.path import log_path
from cfme.utils.quote import quote
from cfme.utils.version import Version


def group_list_dict_by(ld, by):
    result = {}
    for d in ld:
        result[d[by]] = d
    return result


def jenkins_artifact_url(jenkins_username, jenkins_token, jenkins_url, jenkins_job, jenkins_build,
        artifact_path):
    url = '{}/job/{}/{}/artifact/{}'.format(jenkins_url, jenkins_job, jenkins_build, artifact_path)
    scheme, netloc, path, query, fragment = urlsplit(url)
    netloc = '{}:{}@{}'.format(jenkins_username, jenkins_token, netloc)
    return urlunsplit([scheme, netloc, path, query, fragment])


def download_artifact(
        jenkins_username, jenkins_token, jenkins_url, jenkins_job, jenkins_build,
        artifact_path):
    url = '{}/job/{}/{}/artifact/{}'.format(jenkins_url, jenkins_job, jenkins_build, artifact_path)
    return requests.get(
        url, verify=False, auth=HTTPBasicAuth(jenkins_username, jenkins_token)).text


def get_build_numbers(client, job_name):
    return [build['number'] for build in client.get_job_info(job_name)['builds']]


def main(appliance, jenkins_url, jenkins_user, jenkins_token, job_name):
    if not jenkins_user or not jenkins_token:
        try:
            from cfme.utils import conf
            jenkins_user = conf.credentials.jenkins_app.user
            jenkins_token = conf.credentials.jenkins_app.token
        except (AttributeError, KeyError):
            raise ValueError(
                '--jenkins-user and --jenkins-token not provided and credentials yaml does not '
                'contain the jenkins_app entry with user and token')
    appliance_version = str(appliance.version).strip()
    print('Looking for appliance version {} in {}'.format(appliance_version, job_name))
    client = jenkins.Jenkins(jenkins_url, username=jenkins_user, password=jenkins_token)
    build_numbers = get_build_numbers(client, job_name)
    if not build_numbers:
        print('No builds for job {}'.format(job_name))
        return 1

    # Find the builds with appliance version
    eligible_build_numbers = set()
    for build_number in build_numbers:
        try:
            artifacts = client.get_build_info(job_name, build_number)['artifacts']
            if not artifacts:
                raise ValueError()
        except (KeyError, ValueError):
            print('No artifacts for {}/{}'.format(job_name, build_number))
            continue

        artifacts = group_list_dict_by(artifacts, 'fileName')
        if 'appliance_version' not in artifacts:
            print('appliance_version not in artifacts of {}/{}'.format(job_name, build_number))
            continue

        build_appliance_version = download_artifact(
            jenkins_user, jenkins_token, jenkins_url, job_name, build_number,
            artifacts['appliance_version']['relativePath']).strip()

        if not build_appliance_version:
            print('Appliance version unspecified for build {}'.format(build_number))
            continue

        if Version(build_appliance_version) < Version(appliance_version):
            print(
                'Build {} already has lower version ({})'.format(
                    build_number, build_appliance_version))
            print('Ending here')
            break

        if 'coverage-results.tgz' not in artifacts:
            print('coverage-results.tgz not in artifacts of {}/{}'.format(job_name, build_number))
            continue

        if build_appliance_version == appliance_version:
            print('Build {} waas found to contain what is needed'.format(build_number))
            eligible_build_numbers.add(build_number)
        else:
            print(
                'Skipping build {} because it does not have correct version ({})'.format(
                    build_number, build_appliance_version))

    if not eligible_build_numbers:
        print(
            'Could not find any coverage reports for {} in {}'.format(
                appliance_version, job_name))
        return 2

    # Stop the evm service, not needed at all
    print('Stopping evmserverd')
    appliance.evmserverd.stop()
    # Install the coverage tools on the appliance
    print('Installing simplecov')
    appliance.coverage._install_simplecov()
    # Upload the merger
    print('Installing coverage merger')
    appliance.coverage._upload_coverage_merger()
    eligible_build_numbers = sorted(eligible_build_numbers)
    with appliance.ssh_client as ssh:
        if not ssh.run_command('mkdir -p /var/www/miq/vmdb/coverage'):
            print('Could not create /var/www/miq/vmdb/coverage on the appliance!')
            return 3
        # Download all the coverage reports
        for build_number in eligible_build_numbers:
            print('Downloading the coverage report from build {}'.format(build_number))
            download_url = jenkins_artifact_url(
                jenkins_user, jenkins_token, jenkins_url, job_name, build_number,
                'log/coverage/coverage-results.tgz')
            cmd = ssh.run_command(
                'curl -k -o /var/www/miq/vmdb/coverage/tmp.tgz {}'.format(quote(download_url)))
            if not cmd:
                print('Could not download! - {}'.format(str(cmd)))
                return 4
            print('Extracting the coverage report from build {}'.format(build_number))
            extract_command = ' && '.join([
                'cd /var/www/miq/vmdb/coverage',
                'tar xf tmp.tgz --strip-components=1',
                'rm -f tmp.tgz',
            ])
            cmd = ssh.run_command(extract_command)
            if not cmd:
                print('Could not extract! - {}'.format(str(cmd)))
                return 5

        # Now run the merger
        print('Running the merger')
        cmd = ssh.run_command(
            'cd /var/www/miq/vmdb; time bin/rails runner coverage_merger.rb',
            timeout=60 * 60)
        if not cmd:
            print('Failure running the merger - {}'.format(str(cmd)))
            return 6
        else:
            print('Coverage report generation was successful')
            print(str(cmd))
            percentage = re.search(r'LOC\s+\((\d+.\d+%)\)\s+covered\.', str(cmd))
            if percentage:
                print('COVERAGE={};'.format(percentage.groups()[0]))
            else:
                print('COVERAGE=unknown;')

        print('Packing the generated HTML')
        cmd = ssh.run_command('cd /var/www/miq/vmdb/coverage; tar cfz /tmp/merged.tgz merged')
        if not cmd:
            print('Could not compress! - {}'.format(str(cmd)))
            return 7
        print('Grabbing the generated HTML')
        ssh.get_file('/tmp/merged.tgz', log_path.strpath)
        print('Decompressing the generated HTML')
        rc = subprocess.call(
            ['tar', 'xf', log_path.join('merged.tgz').strpath, '-C', log_path.strpath])
        if rc == 0:
            print('Done!')
        else:
            print('Failure to extract')
            return 8


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('jenkins_url')
    parser.add_argument('jenkins_job_name')
    parser.add_argument('work_appliance_ip')
    parser.add_argument('--jenkins-user', default=None)
    parser.add_argument('--jenkins-token', default=None)
    args = parser.parse_args()
    with IPAppliance(args.work_appliance_ip) as appliance:
        exit(main(
            appliance,
            args.jenkins_url,
            args.jenkins_user,
            args.jenkins_token,
            args.jenkins_job_name))
