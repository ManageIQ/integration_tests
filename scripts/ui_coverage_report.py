#!/usr/bin/env python2
"""
This script serves 2 main purposes:
  Firstly, it is used to merge and display UI coverage stats for specified
  jenkins runs.
  It requires an appliance to merge the results which it then downloads to
  the local machine as html.

  Secondly, it can set up UI coverage on an existing appliance or collect
  data from it, if previously set up.


Example usage:
  To pull data from jenkins jobs ('jenkins' mode):
    python scripts/ui_coverage_report.py jenkins \\
      --appliance-ip 192.168.10.10 \\
      --job-name downstream-00z-tests \\
      --build-ids 96,97,101,102,103,104,110 \\
      --verbose

  To setup an appliance with UI coverage ('appliance' mode):
    python scripts/ui_coverage_report.py appliance \\
      --appliance-ip 192.168.10.10 \\
      --setup-coverage \\
      --verbose

  To pull UI coverage data from an appliance ('appliance' mode):
    python scripts/ui_coverage_report.py appliance \\
      --appliance-ip 192.168.10.10 \\
      --verbose
"""

import argparse
import logging
import os
import re
import sys
import tarfile

from jenkinsapi.jenkins import Jenkins
from lxml import html
from utils.conf import cfme_data, credentials as creds
from utils.appliance import IPAppliance
from utils.log import logger
from utils.path import scripts_data_path


# ======= Const defaults =
# ========================
appliance_root_dir = '/var/www/miq/vmdb'
default_out_dir = "/tmp"
coverage_archive_fn = "coverage-results.tgz"
verbose = False
# =======


# ======= Jenkins / params / other =
# ==================================
def parse_cmd_line():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    subparsers = parser.add_subparsers(help='The 2 supported modes')

    parser_j = subparsers.add_parser('jenkins', help='To work with a jenkins server')
    parser_j.set_defaults(mode='jenkins')
    parser_j.add_argument('-a', '--appliance-ip', required=True, type=str,
        help='IP of appliance used to build the report (must match the stream of target version)')
    parser_j.add_argument('-j', '--job-name', required=True, type=str,
        help='Name of the jenkins job')
    parser_j.add_argument('-i', '--init-build-id', type=int,
        help='Number of the build to start from, default is last finished build')
    parser_j.add_argument('-n', '--num-builds', default=5, type=int,
        help='Number of finished builds with artifacts to take data from (going back), '
             'defaults to 5')
    parser_j.add_argument('-b', '--build-ids', type=str,
        help='Comma-separated IDs of builds to collect, overrides --init-build-id and --num-builds')
    parser_j.add_argument('--jenkins-url', type=str,
        help='Jenkins server URL (from yaml by default)')
    parser_j.add_argument('--jenkins-username', type=str,
        help='Jenkins server username (from yaml by default)')
    parser_j.add_argument('--jenkins-password', type=str,
        help='Jenkins server password (from yaml by default)')

    parser_a = subparsers.add_parser('appliance', help='To work with a single appliance')
    parser_a.set_defaults(mode='appliance')
    parser_a.add_argument('-a', '--appliance-ip', required=True, type=str,
        help='IP of appliance to collect data from, must have UI coverage set up')
    parser_a.add_argument('-s', '--setup-coverage', action="store_true",
        help="Will only set up UI coverage on a chosen appliance")

    for subparser in [parser_j, parser_a]:
        subparser.add_argument('-v', '--verbose', action="store_true",
            help="Will print messages to terminal if active, otherwise just debug-level to log")

    args = parser.parse_args()
    if vars(args)['verbose']:
        logger.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logger.debug("Parsed args: %s", args)
    return args


def get_jenkins(url, username, password):

    # We have to do this twice because first attempt sometimes fails with 401
    # Google suggest jenkins ldapurl misconfiguration
    # http://stackoverflow.com/questions/16774866/jenkins-just-login-at-the-second-attempt
    try:
        jenkins = Jenkins(url, username=username, password=password, ssl_verify=False)
    except requests.exceptions.HTTPError:
        jenkins = Jenkins(url, username=username, password=password, ssl_verify=False)
    if verbose:
        logger.debug("Jenkins client:", jenkins)
    logger.debug("Jenkins client: %s", jenkins)
    return jenkins


def decide_build_ids(job, kwargs):
    # We either collect buidls with specific build ids that we were given
    build_ids = kwargs['build_ids']
    if build_ids:
        build_ids = [int(b_id) for b_id in build_ids.split(',')]
    # or we collect --num-builds builds containing artifacts, starting from --init-build-id
    # e.g. 5 builds (with artifacts!) starting from build 100 => 100, 99, 98, 97 and 96
    else:
        init_build_id = kwargs['init_build_id'] or job.get_last_completed_build()
        num_builds = kwargs['num_builds']
        build_ids = []
        for build_id in job.get_build_ids():
            if len(build_ids) >= num_builds:
                break
            build = job.get_build(build_id)
            # If the build doesn't have any artifacts, try another to collect the specified amount
            if build_id <= init_build_id and build.get_artifact_dict():
                build_ids.append(build_id)
    logger.debug("Builds IDs: %s", build_ids)
    return build_ids
# =======


# ======= Coverage related =
# ==========================
def setup_coverage(appliance_ip):
    # TODO
    return True


def fetch_archives(job, build_ids, out_dir=default_out_dir):
    """
    Fetches coverage archives from given jenkins job runs, if available

    Returns: List of paths to coverage archives on local machine
    """
    out_paths = []
    for build_id in build_ids:
        build = job.get_build(build_id)
        art_dict = build.get_artifact_dict()
        if art_dict:
            cov_tgz = art_dict[coverage_archive_fn]
            out_fn = 'cov-{}-{}.tgz'.format(job.name, build_id)
            out_path = os.path.join(out_dir, out_fn)
            try:
                if not verbose:
                    # Disable jenkinsapi error-level warnings
                    # otherwise it will spam the wrong logger (root) with msgs of wrong level...
                    rootLogger = logging.getLogger()
                    orig_level = rootLogger.level
                    rootLogger.setLevel(logging.CRITICAL)
                cov_tgz.save(out_path)
            finally:
                if not verbose:
                    rootLogger.setLevel(orig_level)
            out_paths.append(out_path)
    logger.debug("Archives: %s", out_paths)
    return out_paths


def merge_archives(dest_archive_fn, src_archives, out_dir=default_out_dir):
    """
    Merges all coverage archives from different runs into a single archive

    Returns: Path to the full archive
    """
    dest_archive_path = os.path.join(out_dir, dest_archive_fn)
    dest_tgz = tarfile.open(dest_archive_path, 'w:gz')
    dest_names = dest_tgz.getnames()
    for archive_path in src_archives:
        src_tgz = tarfile.open(archive_path, "r:gz")
        for f in src_tgz.getmembers():
            if f.name not in dest_names:
                dest_tgz.addfile(f, src_tgz.extractfile(f.name))
                dest_names.append(f.name)
    dest_tgz.close()
    logger.debug("Full archive: %s", dest_archive_path)
    return dest_archive_path


def upload_to_appliance(ipappliance, full_archive):
    """
    Uploads the merged archive to the appliance, extracts it and prepares the environment
    """
    ssh = ipappliance.ssh_client
    remote_path = os.path.join(appliance_root_dir, os.path.basename(full_archive))
    ssh.put_file(full_archive, remote_path)
    # simplecov merger script expects the data to be extracted inside
    # $appliance_root_dir/coverage
    ssh.run_command('tar xzf {} --directory {}'.format(remote_path, appliance_root_dir))
    ssh.run_command(
        'cd {}; gem install --no-rdoc --no-ri rails simplecov'.format(appliance_root_dir))
    ssh.run_command('echo "gem \'simplecov\'" > /var/www/miq/vmdb/Gemfile.dev.rb')


def process_and_fetch_report(ipappliance, out_dir=default_out_dir):
    """
    Processes data present on the appliance, creating a viewable HTML report which is then
    downloaded to local machine

    Returns: Coverage percentage and path to the viewable report
    """
    def _process_on_appliance_and_download():
        ssh = ipappliance.ssh_client
        src_path = os.path.join(scripts_data_path.strpath, 'coverage', 'coverage_merger.rb')
        dest_path = os.path.join(appliance_root_dir, 'coverage_merger.rb')
        ssh.put_file(src_path, dest_path)
        rc, out = ssh.run_command(
            'cd {}; bin/rails runner coverage_merger.rb'.format(appliance_root_dir))
        if rc != 0:
            raise Exception("Unable to merge coverage files: {}".format(out))
        # processed data are available under $appliance_root_dir/coverage/merged
        merged_dir = os.path.join(appliance_root_dir, 'coverage', 'merged')
        ssh.run_command('cd {}; tar czf cov-report.tgz .'.format(merged_dir))
        src_path = os.path.join(merged_dir, 'cov-report.tgz')
        dest_path = os.path.join(out_dir, 'cov-report.tgz')
        ssh.get_file(src_path, dest_path)
        return dest_path

    processed_tgz_path = _process_on_appliance_and_download()
    tgz = tarfile.open(processed_tgz_path)
    html_report_dir = os.path.join(out_dir, 'merged-report')
    tgz.extractall(html_report_dir)
    tgz.close()

    # Get the percentage and a link for the report html
    html_report_path = os.path.join(html_report_dir, 'index.html')
    with open(html_report_path, 'r') as index_file:
        index_data = index_file.read().replace('\n', '')
        index_tree = html.fromstring(index_data)
        percentages = index_tree.xpath(
            "//div[@id='AllFiles']//span[@class='covered_percent']/span/text()")
        total_percent_num = re.match("\d+(\.\d+)?", percentages[0]).group(0)

    return total_percent_num, html_report_path
# =======


# ======= Main section =
# ======================
def main(**kwargs):
    if kwargs['verbose']:
        global verbose
        verbose = True

    # Setup coverage on an appliance and quit
    if kwargs['mode'] == 'appliance' and kwargs.get('setup_coverage'):
        logger.info("Setting up UI coverage on {}; this will take a few minutes"
              .format(kwargs['appliance_ip']))
        setup_coverage(kwargs)
        logger.info("Done, exiting...")
        return

    if kwargs['mode'] == 'jenkins':
        jenkins_host = kwargs.get('jenkins_url', None)
        jenkins_user = kwargs.get('jenkins_username', None)
        jenkins_pass = kwargs.get('jenkins_password', None)
        if not jenkins_host:
            jenkins_host = cfme_data.get('jenkins', {}).get('url', None)
        if not jenkins_user or not jenkins_pass:
            jenkins_creds_key = cfme_data.get('jenkins', {}).get('credentials', None)
            if jenkins_creds_key:
                jenkins_user = creds.get(jenkins_creds_key, {}).get('username', None)
                jenkins_pass = creds.get(jenkins_creds_key, {}).get('password', None)

        if not (jenkins_host and jenkins_user and jenkins_pass):
            raise Exception(
                "Jenkins URL / credentials not found (must be present in arguments or in yaml)")

        jenkins = get_jenkins(jenkins_host, jenkins_user, jenkins_pass)

    ipappliance = IPAppliance(kwargs['appliance_ip'])
    logger.info("Stopping appliance's evmserverd service (need as much memory as possible)")
    evm_was_running = ipappliance.is_evm_service_running()
    if evm_was_running:
        ipappliance.stop_evm_service()

    try:
        if kwargs['mode'] == 'jenkins':
            job = jenkins.get_job(kwargs['job_name'])
            build_ids = decide_build_ids(job, kwargs)
            archives = fetch_archives(job, build_ids)
            full_archive = merge_archives('fullcov-{}.tgz'.format(job.name), archives)
            upload_to_appliance(ipappliance, full_archive)

        percent, html_report_path = process_and_fetch_report(ipappliance)
        msg = (
            "Coverage for {}, builds {}, is {}%\n"
            "To see the report, open {} using your browser"
            .format(job.name, build_ids, percent, html_report_path))
        print(msg)
        logger.info(msg)
    finally:
        logger.info("Starting appliance's evmserverd service back up, exiting")
        if evm_was_running:
            ipappliance.start_evm_service()


if __name__ == "__main__":

    # Disable SSL spam (security is important but this is nonsense)
    import requests
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning)

    args = parse_cmd_line()
    kwargs = dict(args._get_kwargs())
    sys.exit(main(**kwargs))

# =======
