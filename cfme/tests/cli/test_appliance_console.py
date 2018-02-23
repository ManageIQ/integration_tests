import pytest
from collections import namedtuple
from wait_for import wait_for
from cfme.utils import os
from cfme.utils.log_validator import LogValidator
from cfme.utils.log import logger
from cfme.utils.conf import hidden
import tempfile
import lxml.etree
import yaml

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
LoginOption = namedtuple('LoginOption', ['name', 'option', 'index'])
TZ = namedtuple('TimeZone', ['name', 'option'])
tzs = [
    TZ('Africa/Abidjan', ('1', '1')),
    TZ('America/Argentina/Buenos_Aires', ('2', '6', '1')),
    TZ('Antarctica/Casey', ('3', 'q', '1')),
    TZ('Arctic/Longyearbyen', ('4', 'q', '1')),
    TZ('Asia/Aden', ('5', '1')),
    TZ('Atlantic/Azores', ('6', 'q', '1')),
    TZ('Australia/Adelaide', ('7', 'q', '1')),
    TZ('Europe/Amsterdam', ('8', '1')),
    TZ('Indian/Antananarivo', ('9', 'q', '1')),
    TZ('Pacific/Apia', ('10', '1')),
    TZ('UTC', ('11',))
]


@pytest.mark.smoke
def test_appliance_console(appliance):
    """'ap | tee /tmp/opt.txt)' saves stdout to file, 'ap' launch appliance_console."""
    command_set = ('ap | tee -a /tmp/opt.txt', 'ap')
    appliance.appliance_console.run_commands(command_set)
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Virtual Appliance'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Database:'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Version:'"
                                            .format(appliance.product_name))


def test_appliance_console_set_hostname(appliance):
    """'ap' launch appliance_console, '' clear info screen, '1' loads network settings, '5' gives
    access to set hostname, 'hostname' sets new hostname."""

    hostname = 'test.example.com'
    command_set = ('ap', '', '1', '5', hostname,)
    appliance.appliance_console.run_commands(command_set)

    def is_hostname_set(appliance):
        assert appliance.ssh_client.run_command("hostname -f | grep {hostname}"
            .format(hostname=hostname))
    wait_for(is_hostname_set, func_args=[appliance])
    return_code, output = appliance.ssh_client.run_command("hostname -f")
    assert output.strip() == hostname
    assert return_code == 0


@pytest.mark.parametrize('timezone', tzs, ids=[tz.name for tz in tzs])
def test_appliance_console_set_timezone(timezone, temp_appliance_preconfig_modscope):
    """'ap' launch appliance_console, '' clear info screen, '2' set timezone, 'opt' select
    region, 'timezone' selects zone, 'y' confirm slection, '' finish."""
    command_set = ('ap', '', '2') + timezone[1] + ('y', '')
    temp_appliance_preconfig_modscope.appliance_console.run_commands(command_set)

    temp_appliance_preconfig_modscope.appliance_console.timezone_check(timezone)


def test_appliance_console_internal_db(app_creds, unconfigured_appliance):
    """'ap' launch appliance_console, '' clear info screen, '5' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'n' don't create dedicated db, '0'
    db region number, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 360), '')
    unconfigured_appliance.appliance_console.run_commands(command_set)
    unconfigured_appliance.wait_for_evm_service()
    unconfigured_appliance.wait_for_web_ui()


def test_appliance_console_internal_db_reset(temp_appliance_preconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5' setup db, '4' reset db, 'y'
    confirm db reset, '1' db region number + wait 360 secs, '' continue"""

    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    command_set = ('ap', '', '5', '4', 'y', TimedCommand('1', 360), '')
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl start evmserverd')
    temp_appliance_preconfig_funcscope.wait_for_evm_service()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


def test_appliance_console_dedicated_db(unconfigured_appliance, app_creds):
    """'ap' launch appliance_console, '' clear info screen, '5' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'y' create dedicated db, 'pwd'
    db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    unconfigured_appliance.appliance_console.run_commands(command_set)
    wait_for(lambda: unconfigured_appliance.db.is_dedicated_active)


def test_appliance_console_ha_crud(unconfigured_appliances, app_creds):
    """Testing HA configuration with 3 appliances.

    Appliance one configuring dedicated database, 'ap' launch appliance_console,
    '' clear info screen, '5' setup db, '1' Creates v2_key, '1' selects internal db,
    '1' use partition, 'y' create dedicated db, 'pwd' db password, 'pwd' confirm db password + wait
    360 secs and '' finish.

    Appliance two creating region in dedicated database, 'ap' launch appliance_console, '' clear
    info screen, '5' setup db, '2' fetch v2_key, 'app0_ip' appliance ip address, '' default user,
    'pwd' appliance password, '' default v2_key location, '2' create region in external db, '0' db
    region number, 'y' confirm create region in external db 'app0_ip', '' ip and default port for
    dedicated db, '' use default db name, '' default username, 'pwd' db password, 'pwd' confirm db
    password + wait 360 seconds and '' finish.

    Appliance one configuring primary node for replication, 'ap' launch appliance_console, '' clear
    info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait 360 seconds to configure, '' finish.


    Appliance three configuring standby node for replication, 'ap' launch appliance_console, ''
    clear info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait 360 seconds to configure, '' finish.


    Appliance two configuring automatic failover of database nodes, 'ap' launch appliance_console,
    '' clear info screen '9' configure application database failover monitor, '1' start failover
    monitor. wait 30 seconds for service to start '' finish.

    Appliance one, stop APPLIANCE_PG_SERVICE and check that the standby node takes over correctly
    and evm starts up again pointing at the new primary database.

    """
    apps = unconfigured_appliances
    app0_ip = apps[0].hostname
    app1_ip = apps[1].hostname
    pwd = app_creds['password']
    # Configure first appliance as dedicated database
    command_set = ('ap', '', '5', '1', '1', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    apps[0].appliance_console.run_commands(command_set)
    wait_for(lambda: apps[0].db.is_dedicated_active)
    # Configure EVM webui appliance with create region in dedicated database
    command_set = ('ap', '', '5', '2', app0_ip, '', pwd, '', '2', '0', 'y', app0_ip, '', '', '',
        pwd, TimedCommand(pwd, 360), '')
    apps[2].appliance_console.run_commands(command_set)
    apps[2].wait_for_evm_service()
    apps[2].wait_for_web_ui()
    # Configure primary replication node
    command_set = ('ap', '', '6', '1', '1', '', '', pwd, pwd, app0_ip, 'y',
        TimedCommand('y', 60), '')
    apps[0].appliance_console.run_commands(command_set)
    # Configure secondary replication node
    command_set = ('ap', '', '6', '2', '1', '2', '', '', pwd, pwd, app0_ip, app1_ip, 'y',
        TimedCommand('y', 60), '')
    apps[1].appliance_console.run_commands(command_set)
    # Configure automatic failover on EVM appliance
    command_set = ('ap', '', '9', TimedCommand('1', 30), '')
    apps[2].appliance_console.run_commands(command_set)

    def is_ha_monitor_started(appliance):
        assert appliance.ssh_client.run_command(
            "cat /var/www/miq/vmdb/config/failover_databases.yml | grep {}".format(app1_ip))
    wait_for(is_ha_monitor_started, func_args=[apps[2]], timeout=300, handle_exception=True)
    # Cause failover to occur
    rc, out = apps[0].ssh_client.run_command('systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
    assert rc == 0, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(out)

    def is_failover_started(appliance):
        assert appliance.ssh_client.run_command(
            "cat /var/www/miq/vmdb/log/ha_admin.log | grep 'Starting to execute failover'")
    wait_for(is_failover_started, func_args=[apps[2]], timeout=450, handle_exception=True)
    apps[2].wait_for_evm_service()
    apps[2].wait_for_web_ui()


def test_appliance_console_external_db(temp_appliance_unconfig_funcscope, app_creds, appliance):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '2' fetch v2_key,
    'ip' address to fetch from, '' default username, 'pwd' db password, '' default v2_key location,
    '3' join external region, 'port' ip and port of joining region, '' use default db name, ''
    default username, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    ip = appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', '', '5', '2', ip, '', pwd, '', '3', ip, '', '', '',
        pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_appliance_console_external_db_create(
        app_creds, dedicated_db_appliance, unconfigured_appliance_secondary):
    """'ap' launch appliance_console, '' clear info screen, '5' setup db, '1' create v2_key,
    '2' create region in external db, '0' db region number, 'y' confirm create region in external db
    'ip', '' ip and port for dedicated db, '' use default db name, '' default username, 'pwd' db
    password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    ip = dedicated_db_appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '2', '0', 'y', ip, '', '', '', pwd,
        TimedCommand(pwd, 300), '')
    unconfigured_appliance_secondary.appliance_console.run_commands(command_set)
    unconfigured_appliance_secondary.wait_for_evm_service()
    unconfigured_appliance_secondary.wait_for_web_ui()


def test_appliance_console_extend_storage(unconfigured_appliance):
    """'ap' launches appliance_console, '' clears info screen, '10' extend storage, '1' select
    disk, 'y' confirm configuration and '' complete."""

    command_set = ('ap', '', '10', '1', 'y', '')
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended)


@pytest.mark.uncollect('No IPA servers currently available')
def test_appliance_console_ipa(ipa_creds, configured_appliance):
    """'ap' launches appliance_console, '' clears info screen, '11' setup IPA, 'y' confirm setup
    + wait 40 secs and '' finish."""

    command_set = ('ap', '', '11', ipa_creds['hostname'], ipa_creds['domain'], '',
        ipa_creds['username'], ipa_creds['password'], TimedCommand('y', 40), '')
    configured_appliance.appliance_console.run_commands(command_set)

    def is_sssd_running(configured_appliance):
        assert configured_appliance.ssh_client.run_command("systemctl status sssd | grep running")
    wait_for(is_sssd_running, func_args=[configured_appliance])
    return_code, output = configured_appliance.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0


@pytest.mark.uncollect('No IPA servers currently available')
@pytest.mark.parametrize('auth_type', [
    LoginOption('sso', 'sso_enabled', '1'),
    LoginOption('saml', 'saml_enabled', '2'),
    LoginOption('local_login', 'local_login_disabled', '3')
], ids=['sso', 'saml', 'local_login'])
def test_appliance_console_external_auth(auth_type, app_creds, ipa_crud):
    """'ap' launches appliance_console, '' clears info screen, '12' change ext auth options,
    'auth_type' auth type to change, '4' apply changes."""

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type.option)],
                            hostname=ipa_crud.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    command_set = ('ap', '', '12', auth_type.index, '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type.option)],
                            hostname=ipa_crud.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    command_set = ('ap', '', '12', auth_type.index, '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


@pytest.mark.uncollect('No IPA servers currently available')
def test_appliance_console_external_auth_all(app_creds, ipa_crud):
    """'ap' launches appliance_console, '' clears info screen, '12' change ext auth options,
    'auth_type' auth type to change, '4' apply changes."""

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to true.*', '.*saml_enabled to true.*',
                                '.*local_login_disabled to true.*'],
                            hostname=ipa_crud.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    command_set = ('ap', '', '12', '1', '2', '3', '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to false.*',
                                '.*saml_enabled to false.*', '.*local_login_disabled to false.*'],
                            hostname=ipa_crud.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    command_set = ('ap', '', '12', '1', '2', '3', '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


def test_appliance_console_scap(temp_appliance_preconfig, soft_assert):
    """'ap' launches appliance_console, '' clears info screen, '14' Hardens appliance using SCAP
    configuration, '' complete."""

    command_set = ('ap', '', '14', '')
    temp_appliance_preconfig.appliance_console.run_commands(command_set)

    with tempfile.NamedTemporaryFile('w') as f:
        f.write(hidden['scap.rb'])
        f.flush()
        os.fsync(f.fileno())
        temp_appliance_preconfig.ssh_client.put_file(
            f.name, '/tmp/scap.rb')
    if temp_appliance_preconfig.version >= "5.8":
        rules = '/var/www/miq/vmdb/productization/appliance_console/config/scap_rules.yml'
    else:
        rules = '/var/www/miq/vmdb/gems/pending/appliance_console/config/scap_rules.yml'

    temp_appliance_preconfig.ssh_client.run_command('cd /tmp/ && ruby scap.rb '
        '--rulesfile={rules}'.format(rules=rules))
    temp_appliance_preconfig.ssh_client.get_file(
        '/tmp/scap-results.xccdf.xml', '/tmp/scap-results.xccdf.xml')
    temp_appliance_preconfig.ssh_client.get_file(
        '{rules}'.format(rules=rules), '/tmp/scap_rules.yml')    # Get the scap rules

    with open('/tmp/scap_rules.yml') as f:
        yml = yaml.load(f.read())
        rules = yml['rules']

    tree = lxml.etree.parse('/tmp/scap-results.xccdf.xml')
    root = tree.getroot()
    for rule in rules:
        elements = root.findall(
            './/{{http://checklists.nist.gov/xccdf/1.1}}rule-result[@idref="{}"]'.format(rule))
        if elements:
            result = elements[0].findall('./{http://checklists.nist.gov/xccdf/1.1}result')
            if result:
                soft_assert(result[0].text == 'pass')
                logger.info("{}: {}".format(rule, result[0].text))
            else:
                logger.info("{}: no result".format(rule))
        else:
            logger.info("{}: rule not found".format(rule))
