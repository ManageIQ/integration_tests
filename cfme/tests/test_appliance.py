# -*- coding: utf-8 -*-
"""Tests around the appliance"""

import pytest

from fixtures.pytest_store import store
from utils import db, version

pytestmark = [pytest.mark.smoke, pytest.mark.tier(1)]


def _rpms_present_packages():
    # autogenerate the rpms to test based on the current appliance version
    # and the list of possible packages that can be installed
    current_version = version.current_version()
    possible_packages = [
        'cfme',
        'cfme-appliance',
        'cfme-lib',
        'nfs-utils',
        'nfs-utils-lib',
        'libnfsidmap',
        'mingw32-cfme-host',
        'ipmitool',
        'prince',
        'netapp-manageability-sdk',
        'rhn-client-tools',
        'rhn-check',
        'rhnlib'
    ]

    def package_filter(package):
        package_tests = [
            # stopped shipping this with 5.4
            package == 'mingw32-cfme-host' and current_version >= '5.4',
            # stopped shipping these with 5.5
            package in ('cfme-lib', 'netapp-manageability-sdk') and current_version >= 5.5,
            # nfs-utils-lib was superseded by libnfsidmap in el7/cfme 5.5
            # so filter out nfs-utils-lib on 5.5 and up, and libnfsidmap below 5.5
            package == 'nfs-utils-lib' and current_version >= '5.5',
            package == 'libnfsidmap' and current_version < '5.5',
        ]
        # If any of the package tests eval'd to true, filter this package out
        return not any(package_tests)

    return filter(package_filter, possible_packages)


def test_product_name():
    if store.current_appliance.is_downstream:
        assert store.current_appliance.product_name == 'CFME'
    else:
        assert store.current_appliance.product_name == 'ManageIQ'


@pytest.mark.ignore_stream("upstream")
@pytest.mark.parametrize(('package'), _rpms_present_packages())
def test_rpms_present(ssh_client, package):
    """Verifies nfs-util rpms are in place needed for pxe & nfs operations"""
    exit, stdout = ssh_client.run_command('rpm -q {}'.format(package))
    assert 'is not installed' not in stdout
    assert exit == 0


# this is going to fail on 5.1
def test_selinux_enabled(ssh_client):
    """Verifies selinux is enabled"""
    stdout = ssh_client.run_command('getenforce')[1]
    assert 'Enforcing' in stdout


@pytest.mark.uncollectif(lambda: version.current_version() >= '5.6')
def test_iptables_running(ssh_client):
    """Verifies iptables service is running on the appliance"""
    stdout = ssh_client.run_command('service iptables status')[1]
    assert 'is not running' not in stdout


@pytest.mark.uncollectif(lambda: version.current_version() < '5.6')
def test_firewalld_running(ssh_client):
    """Verifies iptables service is running on the appliance"""
    stdout = ssh_client.run_command('service firewalld status')[1]
    assert 'active (running)' in stdout


# In versions using systemd, httpd is disabled, and started by evmserverd
@pytest.mark.uncollectif(lambda: version.current_version() >= '5.5')
def test_httpd_running(ssh_client):
    """Verifies httpd service is running on the appliance"""
    stdout = ssh_client.run_command('service httpd status')[1]
    assert 'is running' in stdout


@pytest.mark.meta(blockers=[1341242])
@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_journald_running(ssh_client):
    """Verifies systemd-journald service is running on the appliance"""
    stdout = ssh_client.run_command('systemctl status systemd-journald').output
    assert 'active (running)' in stdout


def test_evm_running(ssh_client):
    """Verifies overall evm service is running on the appliance"""
    if version.current_version() < '5.5':
        stdout = ssh_client.run_command('service evmserverd status | grep EVM')[1]
        assert 'started' in stdout.lower()
    else:
        stdout = ssh_client.run_command('systemctl status evmserverd')[1]
        assert 'active (running)' in stdout


@pytest.mark.uncollectif(lambda service: version.current_version() >= '5.5'
    and service == 'iptables')
@pytest.mark.parametrize(('service'), [
    'evmserverd',
    'evminit',
    'sshd',
    'iptables',
    'postgresql',
])
def test_service_enabled(ssh_client, service):
    """Verifies if key services are configured to start on boot up"""
    if service == 'postgresql':
        service = '{}-postgresql'.format(db.scl_name())
    if pytest.store.current_appliance.os_version >= '7':
        cmd = 'systemctl is-enabled {}'.format(service)
    else:
        cmd = 'chkconfig | grep {} | grep -q "5:on"'.format(service)
    result = ssh_client.run_command(cmd)
    assert result.rc == 0, result.output


@pytest.mark.ignore_stream("upstream")
@pytest.mark.parametrize(('proto,port'), [
    ('tcp', 22),
    ('tcp', 80),
    ('tcp', 443),
])
def test_iptables_rules(ssh_client, proto, port):
    """Verifies key iptable rules are in place"""
    # get the current iptables state, nicely formatted for us by iptables-save
    res = ssh_client.run_command('iptables-save')
    # get everything from the input chain
    input_rules = filter(lambda line: line.startswith('-A IN'), res.output.splitlines())

    # filter to make sure we have a rule that matches the given proto and port
    def rule_filter(rule):
        # iptables-save should put all of these in order for us
        # if not, this can be broken up into its individual components
        matches = [
            '-p {proto}',
            '-m {proto} --dport {port}',
            '-j ACCEPT'
        ]
        return all([match.format(proto=proto, port=port) in rule for match in matches])
    assert filter(rule_filter, input_rules)


# this is based on expected changes tracked in github/ManageIQ/cfme_build repo
def test_memory_total(ssh_client):
    """Verifies that the total memory on the box is >= 6GB"""
    stdout = ssh_client.run_command(
        'free -g | grep Mem: | awk \'{ print $2 }\'')[1]
    assert stdout >= 6


# this is based on expected changes tracked in github/ManageIQ/cfme_build repo
def test_cpu_total(ssh_client):
    """Verifies that the total number of cpus is >= 4"""
    stdout = ssh_client.run_command(
        'lscpu | grep ^CPU\(s\): | awk \'{ print $2 }\'')[1]
    assert stdout >= 4


@pytest.mark.ignore_stream("upstream")
def test_certificates_present(ssh_client, soft_assert):
    """Test whether the required product certificates are present."""

    known_certs = ["/etc/rhsm/ca/redhat-uep.pem",
    "/etc/rhsm/ca/candlepin-stage.pem", "/etc/pki/product-default/69.pem",
    "/etc/pki/product/167.pem", "/etc/pki/product/201.pem"]

    for cert in known_certs:
        cert_path_vaild = ssh_client.run_command("test -f '{}'".format(cert))[0] == 0
        if cert_path_vaild:
            rc, output = ssh_client.run_command(
                "openssl verify -CAfile /etc/rhsm/ca/redhat-uep.pem '{}'".format(cert))
        assert rc == 0


@pytest.mark.ignore_stream("upstream")
def test_db_connection(db):
    """Test that the pgsql db is listening externally

    This looks for a row in the miq_databases table, which should always exist
    on an appliance with a working database and UI
    """
    databases = db.session.query(db['miq_databases']).all()
    assert len(databases) > 0


def test_asset_precompiled(ssh_client):
    file_exists = ssh_client.run_command("test -d /var/www/miq/vmdb/public/assets").rc == 0
    assert file_exists, "Assets not precompiled"


@pytest.mark.ignore_stream("upstream")
def test_keys_included(ssh_client, soft_assert):
    keys = ['v0_key', 'v1_key', 'v2_key']
    for k in keys:
        file_exists = ssh_client.run_command("test -e /var/www/miq/vmdb/certs/{}".format(k))[0] == 0
        soft_assert(file_exists, "{} was not included in the build".format(k))
