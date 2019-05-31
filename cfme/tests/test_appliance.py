# -*- coding: utf-8 -*-
"""Tests around the appliance"""
import os

import pytest

from cfme import test_requirements
from cfme.utils import conf
from cfme.utils.blockers import BZ
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
    assert appliance.firewalld.is_active


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
    'db_service',
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
    assert getattr(appliance, service).enabled


@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
def test_firewalld_services_are_active(appliance):
    """Verifies key firewalld services are in place

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
        upstream: no
    """
    manageiq_zone = "manageiq"
    result = appliance.ssh_client.run_command(
        'firewall-cmd --permanent --zone={} --list-services'.format(manageiq_zone))
    assert {'ssh', 'http', 'https'} <= set(result.output.split())

    default_iface_zone = appliance.ssh_client.run_command(
        "firewall-cmd --get-zone-of-interface {}".format(appliance.default_iface)
    ).output.strip()
    assert default_iface_zone == manageiq_zone


@pytest.mark.meta(blockers=[BZ(1712944)])
@pytest.mark.ignore_stream("upstream")
@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
def test_firewalld_active_zone_after_restart(appliance):
    """Verifies key firewalld active zone survives firewalld restart

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        testtype: functional
        casecomponent: Appliance
        upstream: no
    """
    manageiq_zone = "manageiq"

    def get_def_iface_zone():
        default_iface_zone_cmd = appliance.ssh_client.run_command(
            "firewall-cmd --get-zone-of-interface {}".format(appliance.default_iface)
        )
        assert default_iface_zone_cmd.success
        return default_iface_zone_cmd.output.strip()

    assert get_def_iface_zone() == manageiq_zone

    assert appliance.firewalld.restart()

    assert get_def_iface_zone() == manageiq_zone


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


@pytest.mark.meta(blockers=[BZ(1712929, forced_streams=['5.11'])])  # against RHEL
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
    if appliance.ssh_client.run_command('which scl').success:
        # We have the scl command. Therefore we need to check the packages.
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
    lv.wait_for_log_validation()
    appliance.wait_for_web_ui()


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

    appliance.wait_for_web_ui()


@test_requirements.distributed
@pytest.mark.manual('manualonly')
def test_ec2_deploy_cfme_image():
    """
    Bugzilla:
        1413835
    Requirement: CFME image imported as AMI in EC2 environment - should be
    imported automatically with every build

    Polarion:
        assignee: mmojzis
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 4h
        endsin: 5.11
        testSteps:
            1. Deploy appliance:
            c4.xlarge instance type
            default vpc network
            Two disks: one default 41GB, one additional 10GB
            Security group with open port 22 & 443 to world
            select appropriate private key
            2. Associate instance with Elastic IP
            3. Configure database using appliance_console
            4. Start evmserverd
        expectedResults:
            1.
            2.
            3.
            4. CFME appliance should work
    """
    pass


def test_fixauth_dryrun_has_feedback(temp_appliance_preconfig):
    """
    Check whether the fixauth says it is running in dry mode

    Polarion:
        assignee: jhenner
        casecomponent: Appliance
        initialEstimate: 1/60h

    Bugzilla:
        1577303
    """
    appliance = temp_appliance_preconfig
    run_command = appliance.ssh_client.run_command
    dry_run_message = (
        'is executing in dry-run mode, and no actual changes will be made **')
    assert dry_run_message in run_command("fix_auth -d").output
    assert dry_run_message in run_command("fix_auth -d -i invalid").output
    assert dry_run_message in run_command("fix_auth -d --databaseyml").output
    assert dry_run_message not in run_command("fix_auth").output
