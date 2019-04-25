# -*- coding: utf-8 -*-
"""Tests around the appliance"""
import os

import pytest

from cfme import test_requirements
from cfme.utils import conf
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for_decorator

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
@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
def test_rpms_present(appliance, package):
    """Verifies nfs-util rpms are in place needed for pxe & nfs operations

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
    """
    result = appliance.ssh_client.run_command('rpm -q {}'.format(package))
    assert 'is not installed' not in result.output
    assert result.success


@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
def test_selinux_enabled(appliance):
    """Verifies selinux is enabled

    Polarion:
        assignee: jhenner
        initialEstimate: 1/11h
        testtype: functional
        casecomponent: Appliance
    """
    result = appliance.ssh_client.run_command('getenforce').output
    assert 'Enforcing' in result


@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
def test_firewalld_running(appliance):
    """Verifies iptables service is running on the appliance

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    result = appliance.ssh_client.run_command('systemctl status firewalld').output
    assert 'active (running)' in result


@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
def test_evm_running(appliance):
    """Verifies overall evm service is running on the appliance

    Polarion:
        assignee: jhenner
        caseimportance: critical
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
    """
    result = appliance.ssh_client.run_command('systemctl status evmserverd').output
    assert 'active (running)' in result


@pytest.mark.parametrize('service', [
    'evmserverd',
    'evminit',
    'sshd',
    'postgresql',
])
@pytest.mark.uncollectif(
    lambda appliance: appliance.is_pod)
def test_service_enabled(appliance, service):
    """Verifies if key services are configured to start on boot up

    Polarion:
        assignee: jhenner
        caseimportance: critical
        initialEstimate: 1/6h
        testtype: functional
        casecomponent: Appliance
    """
    if service == 'postgresql':
        service = '{}-postgresql'.format(appliance.db.postgres_version)
    if appliance.os_version >= '7':
        cmd = 'systemctl is-enabled {}'.format(service)
    else:
        cmd = 'chkconfig | grep {} | grep -q "5:on"'.format(service)
    result = appliance.ssh_client.run_command(cmd)
    assert result.success, result.output


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
@pytest.mark.parametrize('proto,port', [
    ('tcp', 22),
    ('tcp', 80),
    ('tcp', 443),
])
def test_iptables_rules(appliance, proto, port):
    """Verifies key iptable rules are in place

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
        upstream: no
    """
    # get the current iptables state, nicely formatted for us by iptables-save
    result = appliance.ssh_client.run_command('iptables-save')
    # get everything from the input chain
    input_rules = filter(lambda line: line.startswith('-A IN'), result.output.splitlines())

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
    """Verifies that the total memory on the box is >= 6GB

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
    """
    result = appliance.ssh_client.run_command(r"free -g | grep Mem: | awk '{ print $2 }'")
    assert int(result.output) >= 6


# this is based on expected changes tracked in github/ManageIQ/cfme_build repo
def test_cpu_total(appliance):
    """Verifies that the total number of cpus is >= 4

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
    """
    result = appliance.ssh_client.run_command(r"lscpu | grep ^CPU\(s\): | awk '{ print $2 }'")
    assert int(result.output) >= 4


@pytest.mark.ignore_stream("upstream")
def test_certificates_present(appliance, soft_assert):
    """Test whether the required product certificates are present.

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        upstream: no
        casecomponent: Appliance
    """

    rhsm_ca_cert = '/etc/rhsm/ca/redhat-uep.pem'
    rhsm_url = 'https://subscription.rhn.redhat.com/'
    known_certs = [
        rhsm_ca_cert, '/etc/pki/product-default/69.pem',
        '/etc/pki/product/167.pem', '/etc/pki/product/201.pem'
    ]

    # Ensure subscription URL's cert is trusted...
    assert appliance.ssh_client.run_command(
        'curl --connect-timeout 5 --max-time 10 --retry 10 --retry-delay 0'
        ' --retry-max-time 60 --cacert {ca_cert} {url}'
        .format(ca_cert=rhsm_ca_cert, url=rhsm_url)
    ).success

    for cert in known_certs:
        assert appliance.ssh_client.run_command("test -f '{}'".format(cert)).success
        assert appliance.ssh_client.run_command(
            "openssl verify -CAfile {ca_cert} '{cert_file}'"
            .format(ca_cert=rhsm_ca_cert, cert_file=cert)
        )


@pytest.mark.ignore_stream("upstream")
def test_html5_ssl_files_present(appliance, soft_assert):
    """Test if the certificate and key necessary for HTML 5 Console Support
       is present.  These should have been generated by the
       IPAppliance object.   Note, these files are installed by
       the cfme RPM, so we use rpm verify to make sure they do not verify
       and hence were replaced.

    Polarion:
        assignee: joden
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    cert = conf.cfme_data['vm_console']['cert']
    cert_file = os.path.join(cert.install_dir, 'server.cer')
    key_file = os.path.join(cert.install_dir, 'server.cer.key')
    ssl_files = [cert_file, key_file]

    for ssl_file in ssl_files:
        # Test for files existance
        assert appliance.ssh_client.run_command("test -f '{}'".format(ssl_file)).success


@pytest.mark.ignore_stream("upstream")
def test_db_connection(appliance):
    """Test that the pgsql db is listening externally

    This looks for a row in the miq_databases table, which should always exist
    on an appliance with a working database and UI

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
    """
    databases = appliance.db.client.session.query(appliance.db.client['miq_databases']).all()
    assert len(databases) > 0


def test_asset_precompiled(appliance):
    """
    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
    """
    assert appliance.ssh_client.run_command("test -d /var/www/miq/vmdb/public/assets").success, (
        "Assets not precompiled")


@pytest.mark.ignore_stream("upstream")
def test_keys_included(appliance, soft_assert):
    """
    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        upstream: no
        casecomponent: Appliance
    """
    keys = ['v0_key', 'v1_key', 'v2_key']
    for k in keys:
        soft_assert(appliance.ssh_client.run_command(
            "test -e /var/www/miq/vmdb/certs/{}".format(k)).success,
            "{} was not included in the build".format(k))


def test_appliance_console_packages(appliance):
    """Test that we have no scl packages installed.

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    assert appliance.ssh_client.run_command('scl --list | grep -v rh-ruby').success


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_chrony_conf():
    """
    check that iburst exists within /etc/chrony.conf.

    Bugzilla:
        1308606

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_executing_script():
    """
    check that a script from /var/www/miq/vmdb/tools/ runs correctly as
    expected.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_log_crond():
    """
    check that CROND service does not get stopped after appliance has been
    running.

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_exec_scripts():
    """
    check that scripts in /var/www/miq/vmdb/tools have the executable
    section added to the files.
    #!/usr/bin/env ruby # finds ruby
    require File.expand_path("../config/environment", __dir__) # loads
    rails, only needed if the script needs it

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_appliance_replicate_database_disconnection_with_backlog():
    """
    Test replication re-connect with backlog

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.replication
@pytest.mark.tier(1)
def test_appliance_replicate_database_disconnection():
    """
    test replication re-connection w/ no backlog

    Polarion:
        assignee: mnadeem
        casecomponent: Replication
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_log_error():
    """
    check logs for errors such as

    Bugzilla:
        1392087

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/2h
    """
    pass


def test_codename_in_log(appliance):
    """
    check whether logs contains a mention of appliance codename

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/60h
    """
    log = '/var/www/miq/vmdb/log/evm.log'
    lv = LogValidator(log,
                      matched_patterns=[r'.*Codename: \w+$'],
                      hostname=appliance.hostname)
    lv.fix_before_start()
    appliance.ssh_client.run_command('appliance_console_cli --server=restart')

    @wait_for_decorator
    def codename_in_log():
        try:
            lv.validate_logs()
        except pytest.Fail:
            return False
        else:
            return True


def test_codename_in_stdout(appliance):
    """
    check whether stdout contains a mention of appliance codename

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/60h
    """
    cursor = appliance.ssh_client.run_command(
        'journalctl -u evmserverd --show-cursor | tail -n1').output.split('-- cursor: ')[1]
    appliance.ssh_client.run_command('appliance_console_cli --server=restart')

    @wait_for_decorator
    def codename_in_stdout():
        r = appliance.ssh_client.run_command(
            r'journalctl -u evmserverd -c "{}" | egrep -i "codename: \w+$"'.format(cursor))
        return r.success
