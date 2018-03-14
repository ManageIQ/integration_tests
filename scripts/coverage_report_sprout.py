#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# This is a wrapper script for coverage_report_jenkins.py that handles acquiring an appliance
# through sprout and then calls coverage_report_jenkins.py.
import click
import diaper

from cfme.test_framework.sprout.client import SproutClient
from cfme.utils.appliance import IPAppliance
from cfme.utils.conf import env

# Note we get our logging setup from this load too.
from coverage_report_jenkins import aggregate_coverage
from coverage_report_jenkins import logger


@click.command()
@click.argument('jenkins_url')
@click.argument('version')
@click.option('--jenkins-jobs', 'jenkins_jobs', multiple=True,
    help='Jenkins job names from which to aggregate coverage data')
@click.option('--jenkins-user', 'jenkins_user', default=None,
    help='Jenkins user name')
@click.option('--jenkins-token', 'jenkins_token', default=None,
    help='Jenkins user authentication token')
@click.option('--wave-size', 'wave_size', default=10,
    help='How many coverage tarballs to extract at a time when merging')
def claim_appliance_and_aggregate(jenkins_url, jenkins_jobs, version, jenkins_user, jenkins_token,
        wave_size):
    # TODO: Upstream support
    group = 'downstream-' + ''.join(version.split('.')[:2]) + 'z'
    sprout = SproutClient.from_config()
    logger.info('requesting an appliance from sprout for %s/%s', group, version)
    pool_id = sprout.request_appliances(
        group,
        version=version,
        lease_time=env.sonarqube.scanner_lease)
    logger.info('Requested pool %s', pool_id)
    result = None
    try:
        while not result or not (result['fulfilled'] and result['finished']):
            result = sprout.request_check(pool_id)
        appliance_ip = result['appliances'][0]['ip_address']
        logger.info('Received an appliance with IP address: %s', appliance_ip)
        with IPAppliance(hostname=appliance_ip) as appliance:
            exit(
                aggregate_coverage(
                    appliance,
                    jenkins_url,
                    jenkins_user,
                    jenkins_token,
                    jenkins_jobs,
                    wave_size))
    finally:
        with diaper:
            sprout.destroy_pool(pool_id)


if __name__ == '__main__':
    claim_appliance_and_aggregate()
