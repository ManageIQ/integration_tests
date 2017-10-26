#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import argparse
import diaper

from cfme.test_framework.sprout.client import SproutClient
from cfme.utils.appliance import IPAppliance

from coverage_report_jenkins import main as coverage_report_jenkins


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('jenkins_url')
    parser.add_argument('jenkins_job_name')
    parser.add_argument('version')
    parser.add_argument('--jenkins-user', default=None)
    parser.add_argument('--jenkins-token', default=None)
    args = parser.parse_args()
    # TODO: Upstream support
    group = 'downstream-' + ''.join(args.version.split('.')[:2]) + 'z'
    sprout = SproutClient.from_config()
    print('requesting an appliance from sprout for {}/{}'.format(group, args.version))
    pool_id = sprout.request_appliances(group, version=args.version)
    print('Requested pool {}'.format(pool_id))
    result = None
    try:
        while not result or not (result['fulfilled'] and result['finished']):
            result = sprout.request_check(pool_id)
        appliance_ip = result['appliances'][0]['ip_address']
        print('received an appliance with IP address: {}'.format(appliance_ip))
        with IPAppliance(appliance_ip) as appliance:
            exit(
                coverage_report_jenkins(
                    appliance,
                    args.jenkins_url,
                    args.jenkins_user,
                    args.jenkins_token,
                    args.jenkins_job_name))
    finally:
        with diaper:
            sprout.destroy_pool(pool_id)
