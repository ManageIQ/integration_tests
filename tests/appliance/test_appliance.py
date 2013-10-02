''' Tests around the appliance '''

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium
]


@pytest.mark.parametrize(('package'), [
    'nfs-utils',
    'nfs-utils-lib',
    'mingw32-cfme-host'
])
def test_rpms_present(ssh_client, package):
    ''' Verifies nfs-util rpms are in place needed for pxe & nfs operations'''
    exit, stdout = ssh_client.run_command('rpm -q %s' % package)
    Assert.true('is not installed' not in stdout)
    Assert.equal(exit, 0)


# this is going to fail on 5.1
def test_selinux_enabled(ssh_client):
    ''' Verfies selinux is enabled '''
    stdout = ssh_client.run_command('getenforce')[1]
    Assert.contains('Enforcing', stdout)


def test_iptables_running(ssh_client):
    ''' Verifies iptables service is running on the appliance'''
    stdout = ssh_client.run_command('service iptables status')[1]
    Assert.true('is not running' not in stdout)


def test_httpd_running(ssh_client):
    ''' Verifies httpd service is running on the appliance '''
    stdout = ssh_client.run_command('service httpd status')[1]
    Assert.contains('is running', stdout)


def test_evm_running(ssh_client):
    ''' Verifies overall evm service is running on the appliance '''
    stdout = ssh_client.run_command('service evmserverd status | grep EVM')[1]
    Assert.contains('started', stdout)


@pytest.mark.parametrize(('service'), [
    'evmserverd',
    'sshd',
    'iptables',
    'postgresql92-postgresql',
])
def test_chkconfig_on(ssh_client, service):
    ''' Verifies if key services are configured to start on boot up '''
    stdout = ssh_client.run_command('chkconfig | grep ' + service)[1]
    Assert.contains('5:on', stdout)


@pytest.mark.parametrize(('rule'), [
    'ACCEPT     tcp  --  anywhere             anywhere            state NEW tcp dpt:ssh',
    'ACCEPT     tcp  --  anywhere             anywhere            state NEW tcp dpt:http',
    'ACCEPT     tcp  --  anywhere             anywhere            state NEW tcp dpt:https'
])
def test_iptables_rules(ssh_client, rule):
    ''' Verifies key iptable rules are in place '''
    stdout = ssh_client.run_command('iptables -L')[1]
    Assert.contains(rule, stdout)


# this is based on expected changes tracked in github/ManageIQ/cfme_build repo
def test_memory_total(ssh_client):
    ''' Verifies that the total memory on the box is >= 6GB '''
    stdout = ssh_client.run_command(
        'free -g | grep Mem: | awk \'{ print $2 }\'')[1]
    Assert.true(stdout >= 6)


# this is based on expected changes tracked in github/ManageIQ/cfme_build repo
def test_cpu_total(ssh_client):
    ''' Verifies that the total number of cpus is >= 4 '''
    stdout = ssh_client.run_command(
        'lscpu | grep ^CPU\(s\): | awk \'{ print $2 }\'')[1]
    Assert.true(stdout >= 4)

# TODO
'''
    checks around postgres listening externally, etc
        need to wait for configurable internal db to drop first
'''
