# -*- coding: utf-8 -*-
"""Tests around the appliance"""

import os
import pytest
from fixtures.pytest_store import store
from cfme.utils import conf, version

pytestmark = [pytest.mark.smoke, pytest.mark.tier(1)]


@pytest.mark.ignore_stream("upstream")
@pytest.mark.parametrize('package', [
    'cfme',
    'cfme-appliance',
    'nfs-utils',
    'libnfsidmap',
    'ipmitool',
    'prince',
    'rhn-client-tools',
    'rhn-check',
    'rhnlib',
])
@pytest.mark.uncollectif(
    lambda package: "rhn" in package and store.current_appliance.is_pod)
def test_rpms_present(appliance, package):
    """Verifies nfs-util rpms are in place needed for pxe & nfs operations"""
    exit, stdout = appliance.ssh_client.run_command('rpm -q {}'.format(package))
    assert 'is not installed' not in stdout
    assert exit == 0


@pytest.mark.uncollectif(store.current_appliance.is_pod)
def test_selinux_enabled(appliance):
    """Verifies selinux is enabled"""
    stdout = appliance.ssh_client.run_command('getenforce')[1]
    assert 'Enforcing' in stdout


@pytest.mark.uncollectif(lambda: version.current_version() >= '5.6', reason='Only valid for <5.6')
@pytest.mark.uncollectif(store.current_appliance.is_pod)
def test_iptables_running(appliance):
    """Verifies iptables service is running on the appliance"""
    stdout = appliance.ssh_client.run_command('systemctl status iptables')[1]
    assert 'is not running' not in stdout


@pytest.mark.uncollectif(lambda: version.current_version() < '5.6', reason='Only valid for >5.7')
@pytest.mark.uncollectif(store.current_appliance.is_pod)
def test_firewalld_running(appliance):
    """Verifies iptables service is running on the appliance"""
    stdout = appliance.ssh_client.run_command('systemctl status firewalld')[1]
    assert 'active (running)' in stdout


def test_evm_running(appliance):
    """Verifies overall evm service is running on the appliance"""
    stdout = appliance.ssh_client.run_command('systemctl status evmserverd')[1]
    assert 'active (running)' in stdout


@pytest.mark.parametrize('service', [
    'evmserverd',
    'evminit',
    'sshd',
    'postgresql',
])
@pytest.mark.uncollectif(
    lambda service: service in ['sshd', 'postgresql'] and store.current_appliance.is_pod)
def test_service_enabled(appliance, service):
    """Verifies if key services are configured to start on boot up"""
    if service == 'postgresql':
        service = '{}-postgresql'.format(appliance.db.postgres_version)
    if pytest.store.current_appliance.os_version >= '7':
        cmd = 'systemctl is-enabled {}'.format(service)
    else:
        cmd = 'chkconfig | grep {} | grep -q "5:on"'.format(service)
    result = appliance.ssh_client.run_command(cmd)
    assert result.rc == 0, result.output


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(store.current_appliance.is_pod)
@pytest.mark.parametrize('proto,port', [
    ('tcp', 22),
    ('tcp', 80),
    ('tcp', 443),
])
def test_iptables_rules(appliance, proto, port):
    """Verifies key iptable rules are in place"""
    # get the current iptables state, nicely formatted for us by iptables-save
    res = appliance.ssh_client.run_command('iptables-save')
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
def test_memory_total(appliance):
    """Verifies that the total memory on the box is >= 6GB"""
    stdout = appliance.ssh_client.run_command(
        'free -g | grep Mem: | awk \'{ print $2 }\'')[1]
    assert stdout >= 6


# this is based on expected changes tracked in github/ManageIQ/cfme_build repo
def test_cpu_total(appliance):
    """Verifies that the total number of cpus is >= 4"""
    stdout = appliance.ssh_client.run_command(
        'lscpu | grep ^CPU\(s\): | awk \'{ print $2 }\'')[1]
    assert stdout >= 4


@pytest.mark.ignore_stream("upstream")
def test_certificates_present(appliance, soft_assert):
    """Test whether the required product certificates are present."""

    known_certs = ["/etc/rhsm/ca/redhat-uep.pem",
    "/etc/rhsm/ca/candlepin-stage.pem", "/etc/pki/product-default/69.pem",
    "/etc/pki/product/167.pem", "/etc/pki/product/201.pem"]

    for cert in known_certs:
        cert_path_vaild = appliance.ssh_client.run_command("test -f '{}'".format(cert))[0] == 0
        if cert_path_vaild:
            rc, output = appliance.ssh_client.run_command(
                "openssl verify -CAfile /etc/rhsm/ca/redhat-uep.pem '{}'".format(cert))
        assert rc == 0


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda: version.current_version() < '5.8', reason='Only valid for >5.8')
def test_html5_ssl_files_present(appliance, soft_assert):
    """Test if the certificate and key necessary for HTML 5 Console Support
       is present.  These should have been generated by the
       IPAppliance object.   Note, these files are installed by
       the cfme RPM, so we use rpm verify to make sure they do not verify
       and hence were replaced.
    """
    cert = conf.cfme_data['vm_console']['cert']
    cert_file = os.path.join(cert.install_dir, 'server.cer')
    key_file = os.path.join(cert.install_dir, 'server.cer.key')
    ssl_files = [cert_file, key_file]

    for ssl_file in ssl_files:
        # Test for files existance
        assert appliance.ssh_client.run_command("test -f '{}'".format(ssl_file)) == 0


@pytest.mark.ignore_stream("upstream")
def test_db_connection(appliance):
    """Test that the pgsql db is listening externally

    This looks for a row in the miq_databases table, which should always exist
    on an appliance with a working database and UI
    """
    databases = appliance.db.client.session.query(appliance.db.client['miq_databases']).all()
    assert len(databases) > 0


def test_asset_precompiled(appliance):
    file_exists = appliance.ssh_client.run_command(
        "test -d /var/www/miq/vmdb/public/assets").rc == 0
    assert file_exists, "Assets not precompiled"


@pytest.mark.ignore_stream("upstream")
def test_keys_included(appliance, soft_assert):
    keys = ['v0_key', 'v1_key', 'v2_key']
    for k in keys:
        file_exists = appliance.ssh_client.run_command(
            "test -e /var/www/miq/vmdb/certs/{}".format(k))[0] == 0
        soft_assert(file_exists, "{} was not included in the build".format(k))
