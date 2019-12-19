import tempfile
from collections import namedtuple

import lxml.etree
import pytest
import yaml
from wait_for import TimedOutError
from wait_for import wait_for

from cfme import test_requirements
from cfme.utils import os
from cfme.utils.appliance.console import waiting_for_ha_monitor_started
from cfme.utils.blockers import BZ
from cfme.utils.conf import hidden
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator

pytestmark = [
    test_requirements.app_console,
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason="cli isn't supported in pod appliance")
]

evm_log = '/var/www/miq/vmdb/log/evm.log'

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
RETURN = ''

ext_auth_options = [
    LoginOption('sso', 'sso_enabled', '1'),
    LoginOption('saml', 'saml_enabled', '2'),
    LoginOption('local_login', 'local_login_disabled', '4')
]


@pytest.mark.rhel_testing
@pytest.mark.smoke
@pytest.mark.tier(2)
def test_appliance_console(appliance):
    """'ap | tee /tmp/opt.txt)' saves stdout to file, 'ap' launch appliance_console.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/12h
    """
    command_set = ('ap | tee -a /tmp/opt.txt', 'ap')
    appliance.appliance_console.run_commands(command_set, timeout=120)
    logger.info(appliance.ssh_client.run_command("cat /tmp/opt.txt"))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Virtual Appliance'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Database:'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Version:'"
                                            .format(appliance.product_name))


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_set_hostname(configured_appliance):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '1' loads network settings,
    4. '5' gives access to set hostname,
    5. 'hostname' sets new hostname.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """

    hostname = 'test.example.com'
    command_set = ('ap', RETURN, '1', '5', hostname, RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=30)

    def is_hostname_set(appliance):
        return appliance.ssh_client.run_command("hostname -f | grep {hostname}"
                                                .format(hostname=hostname)).success
    wait_for(is_hostname_set, func_args=[configured_appliance])
    result = configured_appliance.ssh_client.run_command("hostname -f")
    assert result.success
    assert result.output.strip() == hostname


@pytest.mark.rhel_testing
@pytest.mark.parametrize('timezone', tzs, ids=[tz.name for tz in tzs])
@pytest.mark.tier(2)
def test_appliance_console_set_timezone(timezone, temp_appliance_preconfig_modscope):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '2' set timezone,
    4. 'opt' select region,
    5. 'timezone' selects zone,
    6. 'y' confirm slection,
    7. RETURN finish.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    command_set = ('ap', RETURN, '2') + timezone[1] + ('y', RETURN)
    temp_appliance_preconfig_modscope.appliance_console.run_commands(command_set)

    temp_appliance_preconfig_modscope.appliance_console.timezone_check(timezone)


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.11")  # Removed from appliance console in 5.11, BZ 1745895
def test_appliance_console_datetime(temp_appliance_preconfig_funcscope):
    """Grab fresh appliance and set time and date through appliance_console and check result

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    app = temp_appliance_preconfig_funcscope
    if app.chronyd.running:
        app.chronyd.stop()

    command_set = ('ap', RETURN, '3', 'y', '2020-10-20', '09:58:00', 'y', RETURN, RETURN)
    app.appliance_console.run_commands(command_set, timeout=30)

    def date_changed():
        appliance_time = str(app.ssh_client.run_command("date +%F-%T"))
        return "2020-10-20-10:00" in str(appliance_time)
    try:
        wait_for(date_changed, timeout=180)
    except TimedOutError:
        raise AssertionError("appliance time doesn't match to set one")


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_internal_db(app_creds, unconfigured_appliance):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '7' setup db,
    4. '1' Creates v2_key,
    5. '1' selects internal db,
    6. '2' choose /dev/vdb as disk
    7. 'n' don't create dedicated db,
    8. '0' db region number,
    9. 'pwd' db password,
    10. 'pwd' confirm db password + wait 360 secs
    11. RETURN finish.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/4h
    """

    pwd = app_creds['password']
    command_set = ('ap', RETURN, '7', '1', '1', '2', 'n', '0', pwd, TimedCommand(pwd, 360), RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set)
    unconfigured_appliance.evmserverd.wait_for_running()
    unconfigured_appliance.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_internal_db_reset(temp_appliance_preconfig_funcscope):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '5' setup db,
    4. '4' reset db,
    5. 'y' confirm db reset,
    6. '1' db region number + wait 360 secs,
    7. RETURN continue

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """

    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    command_set = ('ap', RETURN, '5', '4', 'y', TimedCommand('1', 360), RETURN)
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl start evmserverd')
    temp_appliance_preconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_dedicated_db(unconfigured_appliance, app_creds):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '7' setup db,
    4. '1' Creates v2_key,
    5. '1' selects internal db,
    6. '2' use /dev/vdb partition,
    7. 'y' create dedicated db,
    8. 'pwd' db password,
    9. 'pwd' confirm db password + wait 360 secs
    10. RETURN finish.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/3h
        testtype: structural
    """

    pwd = app_creds['password']
    command_set = ('ap', RETURN, '7', '1', '1', '2', 'y', pwd, TimedCommand(pwd, 360), RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set)
    wait_for(lambda: unconfigured_appliance.db.is_dedicated_active)


@pytest.mark.tier(2)
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


    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1h
        testtype: structural
    """
    apps = unconfigured_appliances
    app0_ip = apps[0].hostname
    app1_ip = apps[1].hostname
    pwd = app_creds['password']
    # Configure first appliance as dedicated database
    command_set = ('ap', RETURN, '7', '1', '1', '2', 'y', pwd, TimedCommand(pwd, 360), RETURN)
    apps[0].appliance_console.run_commands(command_set)
    wait_for(lambda: apps[0].db.is_dedicated_active)
    # Configure EVM webui appliance with create region in dedicated database
    command_set = ('ap', RETURN, '7', '2', app0_ip, RETURN, pwd, RETURN, '2', '0', 'y', app0_ip,
                   RETURN, RETURN, RETURN, pwd, TimedCommand(pwd, 360), RETURN)
    apps[2].appliance_console.run_commands(command_set)
    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_web_ui()
    # Configure primary replication node
    command_set = ('ap', RETURN, '8', '1', '1', RETURN, RETURN, pwd, pwd, app0_ip, 'y',
                   TimedCommand('y', 60), RETURN)
    apps[0].appliance_console.run_commands(command_set)
    # Configure secondary replication node
    command_set = ('ap', RETURN, '8', '2', '2', app0_ip, RETURN, pwd, RETURN, '2', '2', RETURN,
                   RETURN, pwd, pwd, app0_ip, app1_ip, 'y', TimedCommand('y', 360), RETURN)

    apps[1].appliance_console.run_commands(command_set)

    with waiting_for_ha_monitor_started(apps[2], app1_ip, timeout=300):
        # Configure automatic failover on EVM appliance
        command_set = ('ap', RETURN, '10', TimedCommand('1', 30), RETURN)
        apps[2].appliance_console.run_commands(command_set)

    with LogValidator(evm_log,
                      matched_patterns=['Starting to execute failover'],
                      hostname=apps[2].hostname).waiting(timeout=450):
        # Cause failover to occur
        result = apps[0].ssh_client.run_command(
            'systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
        assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_external_db(temp_appliance_unconfig_funcscope, app_creds, appliance):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '7' setup db,
    4. '2' fetch v2_key,
    5. 'ip' address to fetch from,
    6. RETURN default username,
    7. 'pwd' db password,
    8. RETURN default v2_key location,
    9. '3' join external region,
    10. 'port' ip and port of joining region,
    11. RETURN use default db name,
    12. RETURN default username,
    13. 'pwd' db password,
    14. 'pwd' confirm db password + wait 360 secs
    15. RETURN finish.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/2h
        testtype: structural
    """

    ip = appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', RETURN, '7', '2', ip, RETURN, pwd, RETURN, '3', ip, RETURN, RETURN, RETURN,
                   pwd, TimedCommand(pwd, 360), RETURN, RETURN)

    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_external_db_create(
        app_creds, dedicated_db_appliance, unconfigured_appliance_secondary):
    """
    1. 'ap' launch appliance_console,
    2. RETURN clear info screen,
    3. '7' setup db,
    4. '1' create v2_key,
    5. '2' create region in external db,
    6. '0' db region number,
    7. 'y' confirm create region in external db
    8. 'ip',
    9. RETURN ip and port for dedicated db,
    10. RETURN use default db name,
    11. RETURN default username,
    12. 'pwd' db  password,
    13. 'pwd' confirm db password + wait 360 secs,
    14. RETURN finish.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/3h
    """

    ip = dedicated_db_appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', RETURN, '7', '1', '2', '0', 'y', ip, RETURN, RETURN, RETURN, pwd,
        TimedCommand(pwd, 300), RETURN)
    unconfigured_appliance_secondary.appliance_console.run_commands(command_set)
    unconfigured_appliance_secondary.evmserverd.wait_for_running()
    unconfigured_appliance_secondary.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_extend_storage(unconfigured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '11' extend storage,
    4. '2' select disk,
    5. 'y' confirm configuration,
    6. RETURN complete.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/4h
    """
    command_set = ('ap', RETURN, '11', '2', 'y', RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended)


def test_appliance_console_ipa(ipa_crud, configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '12' setup IPA, + wait 40 secs,
    4. RETURN finish.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
    """

    command_set = ('ap', RETURN, '12', ipa_crud.host1, ipa_crud.ipadomain, ipa_crud.iparealm,
                   ipa_crud.ipaprincipal, ipa_crud.bind_password, TimedCommand('y', 60),
                   RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=20)
    configured_appliance.sssd.wait_for_running()
    assert configured_appliance.ssh_client.run_command("cat /etc/ipa/default.conf |"
                                                       "grep 'enable_ra = True'")

    # Unconfigure to cleanup
    # When setup_ipa option selected, will prompt to unconfigure, then to proceed with new config
    command_set = ('ap', RETURN, '12', TimedCommand('y', 40), TimedCommand('n', 5), RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set)
    wait_for(lambda: not configured_appliance.sssd.running)


@pytest.mark.parametrize('auth_type', ext_auth_options, ids=[opt.name for opt in ext_auth_options])
def test_appliance_console_external_auth(auth_type, ipa_crud, configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '13' change ext auth options,
    4. 'auth_type' auth type to change,
    5. '4' apply changes.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
    """
    # TODO this depends on the auth_type options being disabled when the test is run
    # TODO it assumes that first switch is to true, then false.

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type.option)],
                            hostname=configured_appliance.hostname)
    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, '13', auth_type.index, '5', RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=30)
    assert evm_tail.validate(wait="30s")

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type.option)],
                            hostname=configured_appliance.hostname)

    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, '13', auth_type.index, '5', RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=30)
    assert evm_tail.validate(wait="30s")


def test_appliance_console_external_auth_all(configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '13' change ext auth options,
    4. 'auth_type' auth type to change,
    5. '5' apply changes.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
    """

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to true.*',
                                              '.*saml_enabled to true.*',
                                              '.*local_login_disabled to true.*'],
                            hostname=configured_appliance.hostname)
    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, TimedCommand('13', 20), '1', '2', TimedCommand('5', 20),
                   RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set)
    assert evm_tail.validate("30s")

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to false.*',
                                              '.*saml_enabled to false.*',
                                              '.*local_login_disabled to false.*'],
                            hostname=configured_appliance.hostname)

    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, TimedCommand('13', 20), '1', '2', TimedCommand('5', 20),
                   RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set)
    assert evm_tail.validate(wait="30s")


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1769901)])
def test_appliance_console_scap(temp_appliance_preconfig, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '15' Hardens appliance using SCAP configuration,
    4. RETURN complete.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/3h
    """

    command_set = ('ap', RETURN, '15', RETURN, RETURN)
    temp_appliance_preconfig.appliance_console.run_commands(command_set, timeout=30)

    with tempfile.NamedTemporaryFile('w') as f:
        f.write(hidden['scap.rb'])
        f.flush()
        os.fsync(f.fileno())
        temp_appliance_preconfig.ssh_client.put_file(
            f.name, '/tmp/scap.rb')
    rules = '/var/www/miq/vmdb/productization/appliance_console/config/scap_rules.yml'

    temp_appliance_preconfig.ssh_client.run_command('cd /tmp/ && ruby scap.rb '
        '--rulesfile={rules}'.format(rules=rules))
    temp_appliance_preconfig.ssh_client.get_file(
        '/tmp/scap-results.xccdf.xml', '/tmp/scap-results.xccdf.xml')
    temp_appliance_preconfig.ssh_client.get_file(
        '{rules}'.format(rules=rules), '/tmp/scap_rules.yml')    # Get the scap rules

    with open('/tmp/scap_rules.yml') as f:
        yml = yaml.safe_load(f.read())
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


@pytest.mark.tier(1)
def test_appliance_console_dhcp(unconfigured_appliance, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '1' configure network,
    4. '1' configure DHCP,
    5. 'y' confirm IPv4 configuration,
    6. 'y' IPv6 configuration,
    7. Check the changes persist after reboot.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/6h
    """
    command_set = ('ap', RETURN, '1', '1', 'y', TimedCommand('y', 90), RETURN, RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set)
    unconfigured_appliance.reboot(wait_for_web_ui=False)

    soft_assert(unconfigured_appliance.ssh_client.run_command(
        r"ip a show dev eth0 | grep 'inet\s.*dynamic'").success)
    soft_assert(unconfigured_appliance.ssh_client.run_command(
        r"ip a show dev eth0 | grep 'inet6\s.*dynamic'").success)


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[BZ(1766939)])
def test_appliance_console_static_ipv4(unconfigured_appliance, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '1' configure network,
    4. '2' configure static IPv4,
    5. RETURN confirm default IPv4 addr,
    6. RETURN confirm default netmask,
    7. RETURN confirm default gateway,
    8. RETURN confirm default primary DNS,
    9. RETURN confirm default secondary DNS,
    10. RETURN confirm default search order,
    11. 'y' apply static configuration,
    12. Check the static ipv4 persist after reboot to cover the BZ #1766939 #1755398.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/6h
    """
    command_set = ('ap', RETURN, '1', '2', RETURN, RETURN, RETURN, RETURN, RETURN, RETURN, 'y')
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=90)
    unconfigured_appliance.reboot(wait_for_web_ui=False)

    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -4 a show dev eth0 | grep 'inet .*scope global eth0'"))
    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -4 r show dev eth0 | grep 'default via'"))


def test_appliance_console_static_ipv6(unconfigured_appliance, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '1' configure network,
    4. '3' configure static IPv6,
    5. '1::1' set IPv4 addr,
    6. RETURN set deafault prefix length,
    7. '1::f' set IPv6 gateway,
    8. RETURN confirm default primary DNS,
    9. RETURN confirm default secondary DNS,
    10. RETURN confirm default search order,
    11. 'y' apply static configuration,
    12. Check the static ipv6 persist after reboot.

    Polarion:
        assignee: mnadeem
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    command_set = ('ap', RETURN, '1', '3', '1::1', RETURN, '1::f', RETURN, RETURN, RETURN, 'y', '')
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=90)
    unconfigured_appliance.reboot(wait_for_web_ui=False)

    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -6 a show dev eth0 | grep 'inet6 1::1.*scope global'"))
    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -6 r show dev eth0 | grep 'default via 1::f'"))


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_haproxy():
    """
    Test HA setup with HAproxy load balancing.
    https://access.redhat.com/documentation/en-us/red_hat_cloudforms/4.5/h
    tml/high_availability_guide/configuring_haproxy

    Polarion:
        assignee: sbulage
        casecomponent: Replication
        caseimportance: medium
        initialEstimate: 1/2h
        setup: setup HA following https://mojo.redhat.com/docs/DOC-1097888
               setup HAProxy using keepalived and haproxy packages (waiting on
               official documentation)
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_ha_setup_dc():
    """
    Test configuring a high availability setup over multiple data centers.
    Primary + standby in DC1 and standby in DC2
    In order for the slave in DC2 to be promoted to primary, it would need
    to have visibility to > 50% of the nodes. In this
    case, that slave node has visibility to only 1 node, itself, because
    of the network outage. It would need visibility to at
    least 2 nodes in order to be eligible to be promoted. Therefore, it
    cannot be promoted so, it would just be cut off
    from the primary until network connectivity is restored. This is
    specifically the reason for having the extra node on the
    segment with the primary, to ensure that node always has the voting
    majority.

    Polarion:
        assignee: sbulage
        casecomponent: Replication
        initialEstimate: 1/2h
        setup: provision 3 appliances
               setup HA following https://mojo.redhat.com/docs/DOC-1097888
               (https://mojo.redhat.com/docs/DOC-1168738)
               check setup is working be accessing webui
        startsin: 5.8
        testSteps:
            1. Setup HA
                Follow this: https://access.redhat.com/documentation/en-us/red_hat_cloudforms/4.7/
                html/high_availability_guide/installation
        expectedResults:
            1. Confirm primary database server, application server is
               running and it can access the webui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_restart():
    """
    test restarting the appliance

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '16' Stop EVM Server Processes.
            4. 'Y' Stop CFME Server Gracefully.
            5. Wait for some time.
            6. '17' Start EVM Server Processes.
            7. 'Y' to Start CFME server.
            8. Wait for some time.
            9. '21' Quit from appliance_console menu.
            10. Open appliance IP into Browser.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Cross-check service stopped.
            6.
            7.
            8. Cross-check service started.
            9.
            10. Confirm that Appliance is running into browser.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_ha_dc_re_establish():
    """
    Test that upon re-connection of networks the repmgr process continues
    to replicate correctly to the disconnected node within DC2.
    To setup HA follow:
    https://access.redhat.com/documentation/en-us/red_hat_cloudforms/4.7/h
    tml/high_availability_guide//installation

    Polarion:
        assignee: sbulage
        casecomponent: Replication
        initialEstimate: 1/2h
        setup: Restore network connectivity between DC1 and DC2
        startsin: 5.8
        testSteps:
            1. Setup HA
            2. Disconnect DC2.
            3. Check repmgr process replicating to DC1.
            4. Restore network connectivity between DC1 and DC2
        expectedResults:
            1.
            2.
            3.
            4. Confirm replication is working correctly
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_evm_stop():
    """
    test stopping the evm server process

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '16' Stop EVM Server Processes.
            4. 'Y' Stop CFME Server Gracefully.
            5. Wait for some time.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Cross-check service stopped.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_evm_start():
    """
    test starting the evm server process

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Make sure EVM servcer processes are stopped.
            2. '17' Start EVM Server Processes.
            3. 'Y' to Start CFME server.
            4. Wait for some time.
            5. '21' Quit from appliance_console menu.
        expectedResults:
            1.
            2.
            3.
            4. Confirm EVM service is being started.
            5. Confirm replication is working correctly
    """
    pass


@pytest.mark.tier(1)
def test_appliance_console_check_default_ip(appliance):
    """
    test ip settings, checking all the defaults are what is expected.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. '21' Quit.
        expectedResults:
            1. See all default values related to IP
            2. Cross-check default vaules via commandline.
    """
    result = appliance.ssh_client.run_command("appliance_console")
    assert (appliance.hostname in result.output), (
        "ip address is not found on appliance conmsole output."
    )


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_ssl():
    """
    Test ssl connections to postgres database from other appliances.

    Bugzilla:
        1482697

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_restore_ha_standby_node():
    """
    Test backup and restore with a HA setup
    So this should work if you stop the repmgrd service on each of the
    standby nodes before doing the restore and start it after.
    Should be just `systemctl stop rh-postgresql95-repmgr` then `systemctl
    start rh-postgresql95-repmgr` after the restore is finished.

    Polarion:
        assignee: sbulage
        casecomponent: Replication
        caseimportance: medium
        initialEstimate: 1/2h
        setup: provision 3 appliances
               setup HA following https://mojo.redhat.com/docs/DOC-1097888
               backup database server
               make changes to database
               stop database
               restore backup
               check changes are restored and HA continues to work correctly
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_cancel():
    """
    Test option to navigate back from all submenus in appliance_console

    Bugzilla:
        1438844

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_network_conf():
    """
    test network configuration

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '1' configure network.
            4. '2' configure static IPv4.
            5. Set IPv4 address.
            6. '3' configure static IPv6.
            7. Set IPv6 address.
            8. '5' Set Hostname.
            9. '4' Test Network Configuration.
            10. '20' Summary Information.
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
            9.
            10. Check IP and hostname values matches in Summary Information.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_network_conf_negative():
    """
    test network configuration error with invalid settings

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '1' configure network.
            4. '2' configure static IPv4.
            5. Set invalid IPv4 address.
            6. '3' configure static IPv6.
            7. Set invalid IPv6 address.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Check network failure with IPv4.
            6.
            7. Check network failure with IPv6.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_vmdb_httpd():
    """
    check that httpd starts after restarting vmdb

    Bugzilla:
        1337525

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_shutdown():
    """
    test shutting down the appliance

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '19' Shut Down Appliance.
            4. 'Y' Shut Down Appliance now.
            5. Wait for some time.
        expectedResults:
            1.
            2.
            3.
            4.
            5. You will be logged out from SSH.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_static_ip_negative():
    """
    test error on invalid static ip

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '1' configure network.
            4. '2' configure static IPv4.
            5. Set invalid IPv4 address.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Confirm network failure.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_ha_dc_failover():
    """
    Test failing over from DC1 primary to DC1 standby then drop the
    connection between DC1/2. This should create a split brain scenario,
    upon re-establishing connections we need to manually kill/shutdown DC1
    current primary.
    To setup HA follow:
    https://access.redhat.com/documentation/en-us/red_hat_cloudforms/4.7/h
    tml/high_availability_guide//installation

    Polarion:
        assignee: sbulage
        casecomponent: Replication
        initialEstimate: 1/2h
        setup: Setup HA
        startsin: 5.8
        testSteps:
            1. Failover to DC1 standby node, drop connections between DC"s.
            2. Restore network connectivity between DC1 and DC2
            3. Manually kill DC1 current primary if its in a split brain scenario.
        expectedResults:
            1. Confirm HA setup is fine and no connection to between DC's.
            2. Check connectivity between Both DC's
            3. Check DC1 current primary killed/removed.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_logfile():
    """
    Test configuring new log file disk volume.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.7
        testSteps:
            1. Provision new appliance with additional disk
            2. SSH to appliance
            3. Run appliance_console
            4. Select option "Logfile Configuration"
            5. Configure disk
        expectedResults:
            1.
            2.
            3.
            4.
            5. Confirm new logfile disk is configured correctly
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_restore_db_network_negative():
    """
    test restoring database with invalid connection settings

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/3h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '6' Restore Database From Backup.
            4. '2' Network File System (NFS).
            5. Provide wrong information.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Confirm DB restore fails.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_cli_rh_registration():
    """
    Test RHSM registration through cli and check if changes are made
    within the ui

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Provision appliace
            2. SSH to it and run "subscription-manager register"
        expectedResults:
            1.
            2. Check changes within the ui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_extend_storage_negative():
    """
    test extending storage with no additional partition

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '11' Extend Temporary Storage.
        expectedResults:
            1.
            2.
            3. Check there is no extra disk present.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_static_dns():
    """
    test setting secondary dns and check it"s saved as the new default

    Bugzilla:
        1439348

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_apache_reload_log_rotate():
    """
    Check that apache is not reloaded twice after log rotations.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        initialEstimate: 1/12h
        startsin: 5.10
        testtype: structural
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_datetime_negative():
    """
    test setting invalid date/time

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '3' Set Date and Time.
            4. Provider invalid Date and Time.
        expectedResults:
            1.
            2.
            3.
            4. Invalid date/time should not be applied, check for failure there.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_key_fetch_negative():
    """
    test fetching key from fake remote host

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '14' Generate Custom Encryption Key.
            4. 'Y' override exiting Encryption Key.
            5. '2' Fetch key from remote machine.
            6. Provider invalid IP address.
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. Check Encryption Key fetch failure.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_negative():
    """
    test launching appliance_console without a network attached

    Bugzilla:
        1439345

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/6h
        setup: Get an appliance without network attached.
        testSteps:
            1. 'ap' launches appliance_console.
        expectedResults:
            1. Check info screen is blank with Network information.
    """
    pass
