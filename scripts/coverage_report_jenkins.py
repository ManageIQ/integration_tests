#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import click
import jenkins
import os
import py
import re
import requests
import subprocess
import time

from collections import namedtuple
from requests.auth import HTTPBasicAuth
from six.moves.urllib.parse import urlsplit, urlunsplit

from cfme.utils.appliance import IPAppliance
from cfme.utils.conf import env
from cfme.utils.log import logger, add_stdout_handler
from cfme.utils.path import log_path
from cfme.utils.quote import quote
from cfme.utils.version import Version

# Create a few classes using namedtuple.
Build = namedtuple('Build', ['number', 'job', 'coverage_archive'])
Jenkins = namedtuple('Jenkins', ['url', 'user', 'token', 'client'])

# log to stdout too
add_stdout_handler(logger)

# Global variables
coverage_dir = '/coverage'
scan_timeout = env.sonarqube.get('scan_timeout', 600)
scanner_dir = '/root/scanner'
sonar_server_url = env.sonarqube.url
sonar_scanner_url = env.sonarqube.scanner_url


class SSHCmdException(Exception):
    """Exception raised for failing remote commands run through
    utils.ssh.run_command().

    Attributes:
        cmd: command ran.
        msg: explanation of the error.
    """
    def __init__(self, msg, cmd):
        self.cmd = cmd
        self.msg = msg

    def __str__(self):
        return '{}: {}'.format(self.msg, self.cmd)


def ssh_run_cmd(ssh, cmd, error_msg, use_rails=False, **kwargs):
    """Wrapper around utils.ssh.run_command()

    Wraps the utils.ssh.run_command() with standardized error checking
    and logging, such that if a command returns a positive return code
    logging will occur to log:

    - the command that was ran.
    - the exit code.
    - the command output.

    Additionally, an SSHCmdException will be raised with the specified
    error message.

    If use_rails is specified and set to True, then instead of running
    utils.ssh.run_command(), utils.ssh.run_rails_command() is ran.

    Args:
        ssh: util.ssh SSHClient
        cmd: Command to run on the remote system.
        error_msg:  Error message to hadn to SSHCmdException.
        **kwargs:  These arguments will be passed to run_command()
                   along with the command

    Exceptions:
        SSHCmdException
    """
    if use_rails:
        result = ssh.run_rails_command(cmd, **kwargs)
    else:
        result = ssh.run_command(cmd, **kwargs)
    if not result:
        msg = '''CMD: {}
EXIT CODE: {}
COMMAND OUTPUT
===============================================================
{}'''.format(cmd, result.rc, result)
        logger.error(msg)
        raise SSHCmdException(error_msg, cmd)

    return result


def group_list_dict_by(ld, by):
    """Indexes a list of dictionaries.

    Takes a list of dictionaries and creates a structure
    that indexes them by a particular keyword.

    Args:
        ld: list of dictionaries.
        by: key by which to index the dictionaries.

    Returns:
        A dictionary whose keys are the values of the key
        by, and whose values are the dictionaries in the
        original list of dictionaries (i.e. that is an index
        of the dictionaries).
    """
    result = {}
    for d in ld:
        result[d[by]] = d
    return result


def jenkins_artifact_url(jenkins_username, jenkins_token, jenkins_url, jenkins_job, jenkins_build,
        artifact_path):
    """Build Jenkins artifact URL for a particular Jenkins job.

    Args:
        jenkins_username:  Jenkins login.
        jenkins_token:  User token generated in the Jenkins UI.
        jenkins_url:  URL to Jenkins server.
        jenkins_job:  Jenkins Job ID
        jenkins_build: Particular Jenkins Run/Build
        artifactor_path: Path within the artifactor archive to the artifact.

    Returns:
        URL to artifact within the artifactor archive of Jenkins job.
    """
    url = '{}/job/{}/{}/artifact/{}'.format(jenkins_url, jenkins_job, jenkins_build, artifact_path)
    scheme, netloc, path, query, fragment = urlsplit(url)
    netloc = '{}:{}@{}'.format(jenkins_username, jenkins_token, netloc)
    return urlunsplit([scheme, netloc, path, query, fragment])


def download_artifact(
        jenkins_username, jenkins_token, jenkins_url, jenkins_job, jenkins_build,
        artifact_path):
    """Download artifactor artifact

    Gets a particular artifact from a Jenkins job.

    Args:
        jenkins_username:  Jenkins login.
        jenkins_token:  User token generated in the Jenkins UI.
        jenkins_url:  URL to Jenkins server.
        jenkins_job:  Jenkins Job ID
        jenkins_build: Particular Jenkins Run/Build
        artifactor_path: Path within the artifactor archive to the artifact.

    Returns:
        text of download.
    """
    url = '{}/job/{}/{}/artifact/{}'.format(jenkins_url, jenkins_job, jenkins_build, artifact_path)
    return requests.get(
        url, verify=False, auth=HTTPBasicAuth(jenkins_username, jenkins_token)).text


def check_artifact(
        jenkins_username, jenkins_token, jenkins_url, jenkins_job, jenkins_build,
        artifact_path):
    """Verify that artifact exists

    Verify artifact exists for a particular jenkins build and could potentially be
    downloaded

    Args:
        jenkins_username:  Jenkins login.
        jenkins_token:  User token generated in the Jenkins UI.
        jenkins_url:  URL to Jenkins server.
        jenkins_job:  Jenkins Job ID
        jenkins_build: Particular Jenkins/Build
        artifactor_path: Path within the artifactor archive to the artifact.

    Returns:
        True if it exists, False if it does not.
    """
    url = jenkins_artifact_url(
        jenkins_username, jenkins_token, jenkins_url, jenkins_job, jenkins_build, artifact_path)
    return requests.head(
        url, verify=False, auth=HTTPBasicAuth(jenkins_username, jenkins_token)).status_code < 300


def get_build_numbers(client, job_name):
    return [build['number'] for build in client.get_job_info(job_name)['builds']]


def gen_project_key(name, version):
    """Generate sonar project key

    The key will take the form of:

        <project-name>_<major_version>_<minor_version>_<language>_<coverage|static|full-analysis>

    So given the name CFME and version 5.9.0.21, and that CFME is in ruby and we are
    gathering coverage data, our project_key would be:

        CFME_5_9_ruby_coverage

    Args:
        name:   application name
        version:  A version like a.b.c.d where a major version and b is the minor version.
            Actually minimally just need a.b, but any components after a.b are fine.
    Returns:
        a valid Central CI project key for sonarqube.
    """
    # I'm on purpose allowing for any number of version components after 2
    # in case the version string changes (but still has major and minor at
    # at the beginning.
    match = re.search('^(?P<major>\d+)\.(?P<minor>\d+)', version)
    if not match:
        raise ValueError(
            'Start of version string must match: "(\d+).(\d+)", e.g. 5.9  received: {}'.format(
                version))

    project_key = '{name}_{major}_{minor}_ruby_coverage'.format(
        name=name,
        major=match.group('major'),
        minor=match.group('minor'))

    return project_key


def merge_coverage_data(ssh, coverage_dir):
    """Merge coverage data

    Take all the by appliance by process .resultset.json files from
    the coverage archive and merge them into one .resultset.json file.
    Expects the coverage archive to have been extracted to the
    coverage_dir on the appliance to which the ssh client is connected.

    Args:
        ssh:  ssh client
        coverage_dir:  Directory where the coverage archive was extracted.

    Returns:
        Nothing
    """
    logger.info('Merging coverage data')

    # Run the coverage merger script out of the rails root pointing
    # to where the coverage data is installed.   This will generate
    # a directory under the coverage directory called merged, and
    # will have the merged .resultset.json file in it, along with some
    # HTML that was generated by the merger script.
    result = ssh_run_cmd(
        ssh=ssh,
        cmd='coverage_merger.rb --coverageRoot={}'.format(coverage_dir),
        error_msg='Failure running the coverage data merger!',
        use_rails=True,
        timeout=60 * 60)

    # Attempt to get the overall code coverage percentage from the result.
    logger.info('Coverage report generation was successful')
    logger.info(str(result))
    percentage = re.search(r'LOC\s+\((\d+.\d+%)\)\s+covered\.', str(result))
    if percentage:
        logger.info('COVERAGE=%s', percentage.groups()[0])
    else:
        logger.info('COVERAGE=unknown')

    # The sonar-scanner will actually need the .resultset.json file it
    # uses to be in /coverage/.resultset.json (i.e. the root of the coverarage
    # directory), so lets create a symlink:
    merged_resultset = py.path.local(coverage_dir).join('/merged/.resultset.json')
    resultset_link = py.path.local(coverage_dir).join('.resultset.json')
    ssh_run_cmd(
        ssh=ssh,
        cmd='if [ -e "{}" ]; then rm -f {}; fi'.format(resultset_link, resultset_link),
        error_msg='Failed to remove link {}'.format(resultset_link))
    ssh_run_cmd(
        ssh=ssh,
        cmd='ln -s {} {}'.format(merged_resultset, resultset_link),
        error_msg='Failed to link {} to {}'.format(merged_resultset, resultset_link))


def pull_merged_coverage_data(ssh, coverage_dir):
    """Pulls merged coverage data to log directory.

    Args:
        ssh:  ssh client
        coverage_dir:  Directory where the coverage archive was extracted.

    Returns:
        Nothing
    """
    logger.info('Packing the generated HTML')
    ssh_run_cmd(
        ssh=ssh,
        cmd='cd {}; tar cfz /tmp/merged.tgz merged'.format(coverage_dir),
        error_msg='Could not archive results!')
    logger.info('Grabbing the generated HTML')
    ssh.get_file('/tmp/merged.tgz', log_path.strpath)
    logger.info('Locally decompressing the generated HTML')
    subprocess.check_call(
        ['tar', 'xf', log_path.join('merged.tgz').strpath, '-C', log_path.strpath])
    logger.info('Done!')


def install_sonar_scanner(ssh, project_name, project_version, scanner_url, scanner_dir, server_url):
    """ Install sonar-scanner application

    Pulls the sonar-scanner application to the appliance from scanner_url,
    installs it in scanner_dir, and configures it to send its scan data to
    server_url.  It also configures the project config for the scan, setting
    sonar.projectVersion to the appliance version, and setting sonar.sources
    to pick up both sets of sources.

    Args:
        ssh: ssh object (cfme.utils.ssh)
        project_version: Version of project to be scanned.
        scanner_url:  Where to get the scanner from.
        scanner_dir:  Where to install the scanner on the appliance.
        server_url:  Where to send scan data to (i.e. what sonarqube)

    Returns:
        Nothing
    """
    logger.info('Installing sonar scanner on appliance.')
    scanner_zip = '/root/scanner.zip'

    # Create install directory for sonar scanner:
    ssh_run_cmd(
        ssh=ssh,
        cmd='mkdir -p {}'.format(scanner_dir),
        error_msg='Could not create sonar scanner directory, {}, on appliance.'.format(
            scanner_dir))

    # Download the scanner
    ssh_run_cmd(
        ssh=ssh,
        cmd='wget -O {} {}'.format(scanner_zip, quote(scanner_url)),
        error_msg='Could not download scanner software, {}'.format(scanner_url))

    # Extract the scanner
    ssh_run_cmd(
        ssh=ssh,
        cmd='unzip -d {} {}'.format(scanner_dir, scanner_zip),
        error_msg='Could not extract scanner software, {}, to {}'.format(
            scanner_zip, scanner_dir))

    # Note, all the files are underneath one directory under our scanner_dir, but we don't
    # necessarily know the name of that directory.   Yes today, as I write this, the name
    # will be:
    #
    #   sonar-scanner-$version-linux
    #
    # but if they decide to change its name, any code that depended on that would break.   So
    # what will do is go into the one directory that now under our scanner_dir, and move all
    # those files up a directory (into our scanner_dir).   tar has the --strip-components
    # option that would have avoided this, however we are dealing with a zip file and unzip
    # has no similar option.
    ssh_run_cmd(
        ssh=ssh,
        cmd='cd {}; mv $(ls)/* .'.format(scanner_dir),
        error_msg='Could not move scanner files into scanner dir, {}'.format(scanner_dir))

    # Configure the scanner to point to the local sonarqube
    # WARNING:  This definitely makes the assumption the only thing we need in that config is
    #           the variable sonar.host.url set.  If that is ever wrong this will fail, perhaps
    #           mysteriously.  So the ease of this implementation is traded off against that
    #           possible future consequence.
    scanner_conf = '{}/conf/sonar-scanner.properties'.format(scanner_dir)
    ssh_run_cmd(
        ssh=ssh,
        cmd='echo "sonar.host.url={}" > {}'.format(server_url, scanner_conf),
        error_msg='Could write scanner conf, {}s'.format(scanner_conf))

    # Now configure the project
    #
    # We have sources in two directories:
    #
    #   - /opt/rh/cfme-gemset
    #   - /var/www/miq/vmdb
    #
    # It is very important that we set sonar.sources to a comma delimited
    # list of these directories but as relative paths, relative to /.   If
    # we configure them as absolute paths it will only see the files /var/www/miq/vmdb.
    # Don't know why, it just is that way.
    #
    # Hear is an example config:
    #
    #   sonar.projectKey=CFME5.9-11
    #   sonar.projectName=CFME-11
    #   sonar.projectVersion=5.9.0.17
    #   sonar.language=ruby
    #   sonar.sources=opt/rh/cfme-gemset,var/www/miq/vmdb
    project_conf = 'sonar-project.properties'
    local_conf = os.path.join(log_path.strpath, project_conf)
    remote_conf = '/{}'.format(project_conf)
    config_data = '''
sonar.projectKey={project_key}
sonar.projectName={project_name}
sonar.projectVersion={version}
sonar.language=ruby
sonar.sources=opt/rh/cfme-gemset,var/www/miq/vmdb
'''.format(
        project_name=project_name,
        project_key=gen_project_key(name=project_name, version=project_version),
        version=project_version)

    # Write the config file locally and then copy to remote.
    logger.info('Writing %s', local_conf)
    with open(local_conf, 'w') as f:
        f.write(config_data)
    logger.info('Copying %s to appliance as %s', local_conf, remote_conf)
    ssh.put_file(local_conf, remote_conf)


def run_sonar_scanner(ssh, scanner_dir, timeout):
    """Run the sonar scanner

    Run the sonar-scanner.

    Args:
        ssh: ssh object (cfme.utils.ssh)
        scanner_dir:  Installation directory of the sonar-scanner software.
        timeout:  timeout in seconds.

    Returns:
        Nothing
    """
    logger.info('Running sonar scan. This may take a while.')
    logger.info('   timeout=%s', timeout)
    logger.info('   start_time=%s', time.strftime('%T'))
    scanner_executable = '{}/bin/sonar-scanner'.format(scanner_dir)

    # It's very important that we run the sonar-scanner from / as this
    # will allow sonar-scanner to have all CFME ruby source code under
    # one directory as sonar-scanner expects a project to contain all its
    # source under one directory.
    cmd = 'cd /; SONAR_SCANNER_OPTS="-Xmx4096m" {} -X'.format(scanner_executable)
    ssh_run_cmd(ssh=ssh, cmd=cmd, error_msg='sonar scan failed!', timeout=timeout)
    logger.info('   end_time=%s', time.strftime('%T'))


def sonar_scan(ssh, project_name, project_version, scanner_url, scanner_dir, server_url, timeout):
    """Run the sonar scan

    In addition to running the scan, handles the installation of the sonar-scanner software.

    Args:
        ssh: ssh object (cfme.utils.ssh)
        project_name: Name of software.
        project_version: Version of project to be scanned.
        scanner_url:  Where to pull the sonar-scanner software from
        scanner_dir:  Installation directory of sonar-scanner
        server_url:  sonarqube URL.
        timeout:  timeout in seconds

    Returns:
        Nothing
    """
    install_sonar_scanner(ssh, project_name, project_version, scanner_url, scanner_dir, server_url)
    run_sonar_scanner(ssh, scanner_dir, timeout)


def get_eligible_builds(jenkins_data, jenkins_job, cfme_version):
    """Get eligible builds for a specified jenkins job

    An eligible build will be for the specified appliance version, and contain
    the code coverage data.  We return these builds as a list of named tuples
    with the following keys: number, job, coverage_archive.

    Args:
        jenkins_data: (:obj:`collections.namedtuple`) with these
                      attributes:  url, user, token, client
        jenkins_job:  Jenkins job name such as downstream-59z-tests
        cfme_version:  Versuion CFME sources this coverage is against.

    Returns:
        List of eligible builds.  Each build is a named tuple with the following
        keys:  number, job, coverage_archive.
    """
    logger.info('Looking for CFME version %s in %s', cfme_version, jenkins_job)
    build_numbers = get_build_numbers(jenkins_data.client, jenkins_job)
    if not build_numbers:
        raise Exception('No builds for job {}'.format(jenkins_job))

    # Find the builds with appliance version
    eligible_builds = set()
    for build_number in build_numbers:

        # Acquire the artifacts from this build
        try:
            artifacts = jenkins_data.client.get_build_info(jenkins_job, build_number)['artifacts']
            if not artifacts:
                raise ValueError()
        except (KeyError, ValueError):
            logger.info('No artifacts for %s/%s', jenkins_job, build_number)
            continue
        artifacts = group_list_dict_by(artifacts, 'fileName')

        # Make sure that the appliance version is in these artifacts, and it is the
        # the same as the version for which we are gathering coverage data.  If this is
        # not the case this is not an eligible build.
        if 'appliance_version' not in artifacts:
            logger.info('appliance_version not in artifacts of %s/%s', jenkins_job, build_number)
            continue
        build_appliance_version = download_artifact(
            jenkins_data.user,
            jenkins_data.token,
            jenkins_data.url,
            jenkins_job,
            build_number,
            artifacts['appliance_version']['relativePath']).strip()
        if not build_appliance_version:
            logger.info('Appliance version unspecified for build %s', build_number)
            continue

        # Build versions that are less than the target version are invalid
        if Version(build_appliance_version) < Version(cfme_version):
            logger.info(
                'Build %s already has lower version (%s) than target version (%s)',
                build_number, build_appliance_version, cfme_version)
            logger.info('Ending here')
            break

        # We must have the actual coverage data tarball in the artifacts.
        # If we do set it in our build object.
        if 'coverage-results.tgz' not in artifacts:
            logger.info('coverage-results.tgz not in artifacts of %s/%s', jenkins_job, build_number)
            continue

        # We have all the data to instantiate our Build object, so lets do it.
        # Note, we could fill out its data members a little at a time because
        # a namedtuple's data members are immutable.
        build = Build(
            number=build_number,
            job=jenkins_job,
            coverage_archive=artifacts['coverage-results.tgz']['relativePath'])

        if not check_artifact(
                jenkins_data.user,
                jenkins_data.token,
                jenkins_data.url,
                jenkins_job,
                build_number,
                artifacts['coverage-results.tgz']['relativePath']):
            logger.info('Coverage archive could not possibly be downloaded, skipping')
            continue

        if build_appliance_version == cfme_version:
            logger.info('Build %s was found to contain what is needed', build)
            eligible_builds.add(build)
        else:
            logger.info(
                'Skipping build %s because it does not have correct version (%s)',
                build_number,
                build_appliance_version)

    return eligible_builds


def setup_appliance_for_merger(appliance, ssh):
    """Setup appliance for code coverage merger

    Stops the evm service, and then installs the coverage_merger.rb
    script and dependent libraries.

    Args:
        appliance: CFME appliance object
        ssh:  ssh object

    Returns:
        Nothing
    """
    # Stop the evm service, not needed at all
    logger.info('Stopping evmserverd')
    appliance.evmserverd.stop()

    # Install the coverage tools on the appliance
    logger.info('Installing simplecov')
    appliance.coverage._install_simplecov()

    # Upload the merger
    logger.info('Installing coverage merger')
    appliance.coverage._upload_coverage_merger()

    ssh_run_cmd(
        ssh=ssh,
        cmd='mkdir -p {}'.format(coverage_dir),
        error_msg='Could not create coverage directory on the appliance: {}'.format(
            coverage_dir))


def cleanup_coverage_data_wave(ssh, coverage_dir):
    """Cleanup Coverage Data Wave

    Cleans up coverage data leftover from previous wave, and puts the
    merged .resultset.json file in a place it will be picked up for merger
    in the next wave.

    Args:
        ssh:  ssh object
        coverage_dir: directory where coverage data is extracted.

    Returns:
        Nothing

    Raises:

    """
    # Remove result set files.   They are all in directories like: $ip/$pid.
    # So we will remove recursively directories and their contents that start with
    # a number under the coverage directory.
    ssh_run_cmd(
        ssh=ssh,
        cmd='cd {}; rm -rf [0-9]*'.format(coverage_dir),
        error_msg='Could not cleanup old resultset files.')

    # Move merged resultset where it will be treated like a resultset to be merged.
    # We will create a directory like 1/1 and move the merged resultset under that.
    merged_data_dir = py.path.local(coverage_dir).join('/1/1')
    merged_resultset = py.path.local(coverage_dir).join('/merged/.resultset.json')
    ssh_run_cmd(
        ssh=ssh,
        cmd='mkdir -p {}'.format(merged_data_dir),
        error_msg='Could not make new merged data dir: {}'.format(merged_data_dir))
    ssh_run_cmd(
        ssh=ssh,
        cmd='mv {} {}'.format(merged_resultset, merged_data_dir),
        error_msg='Could not move merged result set, {}, to merged data dir, {}'.format(
            merged_resultset, merged_data_dir))

    # Remove merged directory.
    merged_dir = '{}/merged'.format(coverage_dir)
    ssh_run_cmd(
        ssh=ssh,
        cmd='rm -rf {}'.format(merged_dir),
        error_msg='Failed removing merged directory, {}'.format(merged_dir))


def download_and_merge_coverage_data(ssh, builds, jenkins_data, wave_size):
    """Download and merge coverage data in waves.

    Download the coverage tarballs from from the specified builds in waves, merging
    the coverage data a few tarballs at a time.

    Args:
        ssh:  ssh object
        builds:  jenkins job builds from which to pull coverage data.
        jenkins_data:  Named tupple with these attributes:  url, user, token, client
        wave_size:  How many coverage tarballs to extract at a time when merging

    Returns:
        Nothing
    """
    # Note, this is totally based around the fact that coverage_merger.rb
    # doesn't care where a .resultset.json file (i.e. ruby code coverage
    # data file) comes from, such that we can reuse the merged data file
    # with successive waves of coverage data from different jenkins builds.
    #
    # What we will do for each wave is:
    #
    #   * extract some coverage data tarballs.
    #   * merge those.
    #   * cleanup the old data, and make the merged data look like just another
    #     result set.  On the last wave there is no cleanup.
    i = 0
    wave = 1
    while i < len(builds):
        logger.info('Processing wave #%s of coverage tarballs.', wave)
        build_wave = builds[i:i + wave_size]
        for build in build_wave:
            logger.info('Downloading the coverage data from build %s', build.number)
            download_url = jenkins_artifact_url(
                jenkins_data.user,
                jenkins_data.token,
                jenkins_data.url,
                build.job,
                build.number,
                build.coverage_archive)
            ssh_run_cmd(
                ssh=ssh,
                cmd='curl -k -o {} {}'.format(
                    py.path.local(coverage_dir).join('tmp.tgz'),
                    quote(download_url)),
                error_msg='Could not download coverage data from jenkins!')

            logger.info('Extracting the coverage data from build %s', build.number)
            extract_command = ' && '.join([
                'cd {}'.format(coverage_dir),
                'tar xf tmp.tgz --strip-components=1',
                'rm -f tmp.tgz'])
            ssh_run_cmd(
                ssh=ssh,
                cmd=extract_command,
                error_msg='Could not extract coverage data!')

        merge_coverage_data(
            ssh=ssh,
            coverage_dir=coverage_dir)

        # Increment index and wave count
        i += wave_size
        wave += 1

        # We have to cleanup the coverage data we just extracted, move
        # the merged .resultset.json file, and remove the merged data directory.
        # We move the .resultset.json files so that it will be seen as just another
        # result set to merge in the next wave, and the merged data directory is removed
        # so coverage_merger.rb won't get confused by results already being where it drops
        # it's results.   However it is important that we don't do that
        # on the last wave, as we want the merge results to be available after the
        # last wave.
        #
        # XXX: Yes, this is a hack.  Not even one I am proud of.
        if i < len(builds):
            cleanup_coverage_data_wave(
                ssh=ssh,
                coverage_dir=coverage_dir,
            )


def aggregate_coverage(appliance, jenkins_url, jenkins_user, jenkins_token, jenkins_jobs,
        wave_size):
    """ Aggregates code coverage data across the builds of specified jenkins jobs

    Given the version of the specified appliance, find all builds for the specified jenkins
    jobs for that version, and aggregate all the coverage data.   After this do a sonar scan
    of the aggregated coverage data, and send to configured sonarqube.

    Args:
        appliance:  CFME appliance to use as a source of source code, and as a workspace
            for coverage data merger.
        jenkins_url:  URL to Jenkins server
        jenkins_user: Jenkins user name
        jenkins_token:  Jenkins user authentication token.
        jenkins_jobs:  Jenkins job names from which to aggregate coverage data
        wave_size:  How many coverage tarballs to extract at a time when merging

    Returns:
        Nothing
    """
    appliance_version = str(appliance.version).strip()

    # Get Jenkins creds from config if none specified.
    if not jenkins_user or not jenkins_token:
        try:
            from cfme.utils import conf
            jenkins_user = conf.credentials.jenkins_app.user
            jenkins_token = conf.credentials.jenkins_app.token
        except (AttributeError, KeyError):
            raise ValueError(
                '--jenkins-user and --jenkins-token not provided and credentials yaml does not '
                'contain the jenkins_app entry with user and token')

    # Acquire jenkins client and put jenkins data into a named tupple for ease of passing
    # around (i.e. to reduce the number of arguments on functions)
    jenkins_client = jenkins.Jenkins(jenkins_url, username=jenkins_user, password=jenkins_token)
    jenkins_data = Jenkins(
        url=jenkins_url,
        user=jenkins_user,
        token=jenkins_token,
        client=jenkins_client)

    # Get the eligible builds for all jobs specified.
    logger.info('Jenkins Jobs: %s', ' '.join(jenkins_jobs))
    eligible_builds = set()
    for jenkins_job in jenkins_jobs:
        eligible_builds.update(get_eligible_builds(
            jenkins_data,
            jenkins_job,
            appliance_version))
    if not eligible_builds:
        raise Exception(
            'Could not find any coverage reports for {} in {}'.format(
                appliance_version,
                ', '.join(jenkins_jobs)))
    eligible_builds = sorted(eligible_builds, key=lambda build: build.number)

    # Merge data and do sonar scan
    with appliance.ssh_client as ssh:
        setup_appliance_for_merger(appliance, ssh)
        download_and_merge_coverage_data(
            ssh=ssh,
            builds=eligible_builds,
            jenkins_data=jenkins_data,
            wave_size=wave_size)
        pull_merged_coverage_data(
            ssh=ssh,
            coverage_dir=coverage_dir)
        sonar_scan(
            ssh=ssh,
            project_name='CFME',
            project_version=str(appliance.version).strip(),
            scanner_url=sonar_scanner_url,
            scanner_dir=scanner_dir,
            server_url=sonar_server_url,
            timeout=scan_timeout)


@click.command()
@click.argument('jenkins_url')
@click.argument('appliance_ip')
@click.option('--jenkins-jobs', 'jenkins_jobs', multiple=True,
    help='Jenkins job names from which to aggregate coverage data')
@click.option('--jenkins-user', 'jenkins_user', default=None,
    help='Jenkins user name')
@click.option('--jenkins-token', 'jenkins_token', default=None,
    help='Jenkins user authentication token')
@click.option('--wave-size', 'wave_size', default=10,
    help='How many coverage tarballs to extract at a time when merging')
def coverage_report_jenkins(jenkins_url, jenkins_jobs, jenkins_user, jenkins_token, appliance_ip,
        wave_size):
    """Aggregate coverage data from jenkins job(s) and upload to sonarqube"""
    with IPAppliance(hostname=appliance_ip) as appliance:
        exit(aggregate_coverage(
            appliance,
            jenkins_url,
            jenkins_user,
            jenkins_token,
            jenkins_jobs,
            wave_size))


if __name__ == '__main__':
    coverage_report_jenkins()
