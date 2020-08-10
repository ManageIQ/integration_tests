import re
from collections import namedtuple

import fauxfactory
import pytest
from wait_for import TimedOutError
from wait_for import wait_for
from widgetastic.utils import VersionPick

import cfme.utils.auth as authutil
from cfme import test_requirements
from cfme.exceptions import SSHExpectTimeoutError
from cfme.tests.cli import app_con_menu
from cfme.utils import conf
from cfme.utils.appliance.console import waiting_for_ha_monitor_started
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.net import net_check
from cfme.utils.ssh_expect import SSHExpect
from cfme.utils.version import LOWEST

SECONDARY_DNS_REGEX = r'(Secondary DNS:\s*)(?P<secondary_dns>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'

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

IPv4_REGEX = r'(IPv4 Address:\s*)(?P<ipv4>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
IPv6_REGEX = r'(IPv6 Address:\s*)(?P<ipv6>(?<![:.\w])(?:[a-f0-9]{1,4}:){7}[a-f0-9]{1,4}(?![:.\w]))'
CTRL_C = "\x03"
ext_auth_options = [
    LoginOption('sso', 'sso_enabled', '1'),
    LoginOption('saml', 'saml_enabled', '2'),
    LoginOption('local_login', 'local_login_disabled', '4')
]


@pytest.fixture
def secondary_dns(temp_appliance_preconfig_long):
    command_set = ("ap", RETURN)
    result = temp_appliance_preconfig_long.appliance_console.run_commands(command_set, timeout=30)
    secondary_dns = re.search(SECONDARY_DNS_REGEX, result[0]).group("secondary_dns")
    assert secondary_dns, "Secondary DNS not found"
    return secondary_dns


@pytest.fixture
def freeipa_provider():
    # run this on freeipa03 as to not affect tests running on freeipa01
    auth_prov = authutil.get_auth_crud("freeipa03")
    yield auth_prov


@pytest.mark.rhel_testing
@pytest.mark.smoke
@pytest.mark.tier(2)
def test_appliance_console(appliance):
    """'ap | tee /tmp/opt.txt)' saves stdout to file, 'ap' launch appliance_console.

    Polarion:
        assignee: dgaikwad
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
        assignee: dgaikwad
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
        assignee: dgaikwad
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
        assignee: dgaikwad
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
    6.  choose /dev/vdb as disk
    7. 'n' don't create dedicated db,
    8. '0' db region number,
    9. 'pwd' db password,
    10. 'pwd' confirm db password + wait 360 secs
    11. RETURN finish.

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/4h
    """

    pwd = app_creds['password']
    partition = "2" if unconfigured_appliance.version < "5.11" else "1"
    command_set = ('ap', RETURN, app_con_menu["config_db"], '1', '1', partition, 'n', '0', pwd,
                   TimedCommand(pwd, 360), RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=20)
    unconfigured_appliance.evmserverd.wait_for_running()
    unconfigured_appliance.wait_for_miq_ready()


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
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """

    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    command_set = ('ap', RETURN, '5', '4', 'y', TimedCommand('1', 360), RETURN)
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl start evmserverd')
    temp_appliance_preconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_preconfig_funcscope.wait_for_miq_ready()


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
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/3h
        testtype: structural
    """

    pwd = app_creds['password']
    partition = "2" if unconfigured_appliance.version < "5.11" else "1"
    command_set = ('ap', RETURN, app_con_menu["config_db"], '1', '1', partition, 'y', pwd,
                   TimedCommand(pwd, 360), RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=20)
    wait_for(lambda: unconfigured_appliance.db.is_dedicated_active, timeout=900)


@test_requirements.appliance
@test_requirements.ha_proxy
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
        assignee: jhenner
        caseimportance: high
        casecomponent: HAProxy
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
    apps[2].wait_for_miq_ready()
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
        assert result.success, f"Failed to stop APPLIANCE_PG_SERVICE: {result.output}"

    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_miq_ready()


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
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/2h
        testtype: structural
    """

    ip = appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', RETURN, app_con_menu["config_db"], '2', ip, RETURN, pwd, RETURN, '3',
                   ip, RETURN, RETURN, RETURN, pwd, TimedCommand(pwd, 360), RETURN, RETURN)

    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set, timeout=20)
    temp_appliance_unconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_unconfig_funcscope.wait_for_miq_ready()


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
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/3h
    """
    ip = dedicated_db_appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', RETURN, app_con_menu["config_db"], '1', '2', '0', 'y', ip,
                   RETURN, RETURN, RETURN, pwd, TimedCommand(pwd, 300), RETURN)
    unconfigured_appliance_secondary.appliance_console.run_commands(command_set)
    unconfigured_appliance_secondary.evmserverd.wait_for_running(timeout=900)
    unconfigured_appliance_secondary.wait_for_miq_ready()


@pytest.mark.tier(2)
def test_appliance_console_extend_storage(unconfigured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '11' extend storage,
    4.   select disk,
    5. 'y' confirm configuration,
    6. RETURN complete.

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/4h
    """
    partition = "2" if unconfigured_appliance.version < "5.11" else "1"
    command_set = ('ap', RETURN, app_con_menu["ext_temp_storage"], partition, 'y', RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=20)

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended, timeout=900)


def test_appliance_console_ipa(ipa_crud, configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '12' setup IPA, + wait 40 secs,
    4. RETURN finish.

    Polarion:
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
    """

    command_set = ('ap', RETURN, app_con_menu["config_external_auth"], ipa_crud.host1,
                   ipa_crud.ipadomain, ipa_crud.iparealm, ipa_crud.ipaprincipal,
                   ipa_crud.bind_password, TimedCommand('y', 60), RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=20)
    configured_appliance.sssd.wait_for_running()
    assert configured_appliance.ssh_client.run_command("cat /etc/ipa/default.conf |"
                                                       "grep 'enable_ra = True'")

    # Unconfigure to cleanup
    # When setup_ipa option selected, will prompt to unconfigure, then to proceed with new config
    command_set = ('ap', RETURN, app_con_menu["config_external_auth"], TimedCommand('y', 40),
                   TimedCommand('n', 5), RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=20)
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
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
    """
    # TODO this depends on the auth_type options being disabled when the test is run
    # TODO it assumes that first switch is to true, then false.

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=[f'.*{auth_type.option} to true.*'],
                            hostname=configured_appliance.hostname)
    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, app_con_menu["update_ext_auth_opt"], auth_type.index, '5',
                   RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=30)
    assert evm_tail.validate(wait="30s")

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=[f'.*{auth_type.option} to false.*'],
                            hostname=configured_appliance.hostname)

    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, app_con_menu["update_ext_auth_opt"], auth_type.index, '5',
                   RETURN, RETURN)
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
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Auth
        initialEstimate: 1/4h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. press "13" to "Update External Authentication Options"
            4. Press "1" to "Enable Single Sign-On"
            5. Press "2" to "Enable SAML"
            6. press "4" to "Disable Local Login for SAML or OIDC"
            7. press "5" to "Apply updates"
            8. Press "1" to "Disable Single Sign-On"
            9. Press "2" to "Disable SAML"
            10. press "4" to "Enable Local Login for SAML or OIDC"
            11. press "5" to "Apply updates"
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7. Verify log messages
            8.
            9.
            10.
            11. Verify log messages
    """
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to true.*',
                                              '.*saml_enabled to true.*',
                                              '.*local_login_disabled to true.*'],
                            hostname=configured_appliance.hostname)
    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, TimedCommand(app_con_menu["update_ext_auth_opt"], 40), '1',
                   '2', '4', TimedCommand('5', 40), RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=30)
    assert evm_tail.validate("30s")

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to false.*',
                                              '.*saml_enabled to false.*',
                                              '.*local_login_disabled to false.*'],
                            hostname=configured_appliance.hostname)

    evm_tail.start_monitoring()
    command_set = ('ap', RETURN, TimedCommand(app_con_menu["update_ext_auth_opt"], 40), '1',
                   '2', '4', TimedCommand('5', 40), RETURN, RETURN)
    configured_appliance.appliance_console.run_commands(command_set, timeout=30)
    assert evm_tail.validate(wait="30s")


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_scap(temp_appliance_preconfig, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. RETURN clears info screen,
    3. '15' Hardens appliance using SCAP configuration,
    4. RETURN complete.

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/3h
    """

    temp_appliance_preconfig.appliance_console.scap_harden_appliance()
    assert not temp_appliance_preconfig.appliance_console.scap_failures()


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
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/6h
    """
    command_set = ('ap', RETURN, '1', '1', 'y', TimedCommand('y', 90), RETURN, RETURN)
    unconfigured_appliance.appliance_console.run_commands(command_set)
    unconfigured_appliance.reboot(wait_for_miq_ready=False)

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
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/6h
    """
    command_set = ('ap', RETURN, '1', '2', RETURN, RETURN, RETURN, RETURN, RETURN, RETURN, 'y')
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=90)
    unconfigured_appliance.reboot(wait_for_miq_ready=False)

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
        assignee: dgaikwad
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    command_set = ('ap', RETURN, '1', '3', '1::1', RETURN, '1::f', RETURN, RETURN, RETURN, 'y', '')
    unconfigured_appliance.appliance_console.run_commands(command_set, timeout=90)
    unconfigured_appliance.reboot(wait_for_miq_ready=False)

    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -6 a show dev eth0 | grep 'inet6 1::1.*scope global'"))
    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -6 r show dev eth0 | grep 'default via 1::f'"))


@test_requirements.ha_proxy
@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_haproxy():
    """
    Test HA setup with HAproxy load balancing.
    https://access.redhat.com/documentation/en-us/red_hat_cloudforms/4.5/h
    tml/high_availability_guide/configuring_haproxy

    Polarion:
        assignee: jhenner
        casecomponent: HAProxy
        caseimportance: medium
        initialEstimate: 1/2h
        setup: setup HA following https://mojo.redhat.com/docs/DOC-1097888
               setup HAProxy using keepalived and haproxy packages (waiting on
               official documentation)
        startsin: 5.7
    """
    pass


@test_requirements.ha_proxy
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
        assignee: jhenner
        casecomponent: HAProxy
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


@pytest.mark.tier(2)
def test_appliance_console_restart(temp_appliance_preconfig_funcscope):
    """
    test restarting the appliance

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '18' restart appliance.
            4. '1' Restart.
            5. Verify UI (Open appliance IP into Browser.)
        expectedResults:
            1.
            2.
            3.
            4.
            5. Confirm that Appliance is running into browser.
    """
    appliance = temp_appliance_preconfig_funcscope
    restart_appliance_cmd = ("ap", RETURN, app_con_menu["restart_app"], "1", TimedCommand("Y", 0))
    appliance.appliance_console.run_commands(restart_appliance_cmd, timeout=30)

    wait_for(
        net_check, num_sec=180, func_args=["22", appliance.hostname, True, 3],
        message='waiting to shutdown machine',
        fail_condition=True
    )

    appliance.wait_for_miq_ready()
    navigate_to(appliance.server, "LoggedIn")


@test_requirements.ha_proxy
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
        assignee: jhenner
        casecomponent: HAProxy
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


@pytest.mark.tier(2)
def test_appliance_console_evm_stop(temp_appliance_preconfig_funcscope):
    """
    test stopping the evm server process

    Polarion:
        assignee: dgaikwad
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
    appliance = temp_appliance_preconfig_funcscope
    command_set = ("ap", RETURN, app_con_menu["stop_evm"], TimedCommand("Y", 60))
    appliance.appliance_console.run_commands(command_set, timeout=30)
    wait_for(lambda: appliance.evmserverd.running,
             delay=10,
             timeout=300,
             fail_condition=True,
             message='Waiting to stop EVM service',
             fail_func=appliance.evmserverd.running
             )


@pytest.mark.tier(2)
def test_appliance_console_evm_start(request, temp_appliance_preconfig_funcscope):
    """
    test starting the evm server process

    Polarion:
        assignee: dgaikwad
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
    appliance = temp_appliance_preconfig_funcscope
    appliance.evmserverd.stop()
    wait_for(lambda: appliance.is_web_ui_running(), delay=30, num_sec=10, fail_condition=True)

    # Actual testcase starting from here
    start_evm_command = ("ap", RETURN, app_con_menu["start_evm"], "Y", RETURN,
                         RETURN, app_con_menu["quit"])
    appliance.appliance_console.run_commands(start_evm_command, timeout=30)
    appliance.wait_for_miq_ready()
    logged_in_page = appliance.server.login()
    request.addfinalizer(appliance.server.logout)
    assert logged_in_page.is_displayed, "UI is not working after starting the EVM service."


@pytest.mark.tier(1)
def test_appliance_console_check_default_ip(appliance):
    """
    test ip settings, checking all the defaults are what is expected.

    Polarion:
        assignee: dgaikwad
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


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1482697])
def test_appliance_ssl(appliance):
    """
    Testing SSL is enabled or not by default

    Bugzilla:
        1482697

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/3h
        testSteps:
            1. 'cat /opt/rh/cfme-appliance/COPY/etc/manageiq/postgresql.conf.d/
            01_miq_overrides.conf' run above command and grep to "ssl = on" string
            2. run "cat /opt/rh/cfme-appliance/TEMPLATE/var/lib/pgsql/data/pg_hba.conf" on version
             5.11 and "cat /opt/rh/cfme-appliance/TEMPLATE/var/opt/rh/rh-postgresql95/lib/pgsql/
             data/pg_hba.conf" on 5.10 version
        expectedResults:
            1. confirm "ssl = on" text in 01_miq_overrides.conf file
            2. confirm "hostssl all         all   all     md5" text in pg_hba.conf file
    """
    command = (
        "cat /opt/rh/cfme-appliance/COPY/etc/manageiq/postgresql.conf.d/01_miq_overrides.conf"
    )
    result = appliance.ssh_client.run_command(command)
    assert result.success, "SSL check command failed"
    assert "ssl = on" in result.output, "ssl entry not found"

    command = VersionPick(
        {
            LOWEST: (
                "cat /opt/rh/cfme-appliance/TEMPLATE/var/opt/rh/rh-postgresql95/lib/pgsql/data/"
                "pg_hba.conf"
            ),
            "5.11": ("cat /opt/rh/cfme-appliance/TEMPLATE/var/lib/pgsql/data/pg_hba.conf"),
        }
    ).pick(appliance.version)
    result = appliance.ssh_client.run_command(command)
    assert result.success
    assert re.search("hostssl +all +all +all +md5", result.output), "hostssl entry not found"


@test_requirements.ha_proxy
@test_requirements.restore
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
        assignee: jhenner
        casecomponent: HAProxy
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


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1438844])
def test_appliance_console_cancel(appliance):
    """
    Test option to navigate back from all submenus in appliance_console

    Bugzilla:
        1438844

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. type "ap"
            2. press any key to continue
            3. press one menu number and enter key
            4. press CTRL+C ("\x03")
            5. repeat step 1 to step 4 for all menu number from 1 to 19
        expectedResults:
            1.
            2.
            3.
            4. verify welcome console is displayed or not
            5.
    """
    for menu_number in range(1, 20):
        command_set = ("ap", RETURN, str(menu_number), CTRL_C)
        result = appliance.appliance_console.run_commands(command_set, timeout=30)
        assert (
            "Welcome to the CFME Virtual Appliance" in result[0]
        ), f"Unable to go back from {menu_number} menu number."


@pytest.mark.tier(1)
def test_appliance_console_network_conf(temp_appliance_preconfig_long, soft_assert):
    """
    test network configuration

    Polarion:
        assignee: dgaikwad
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
    appliance = temp_appliance_preconfig_long
    command_set = (TimedCommand("ap", 20), RETURN)
    old_result = appliance.appliance_console.run_commands(command_set)
    logger.info('"ap" command output before test run:%s', old_result)

    ipv4 = re.search(IPv4_REGEX, old_result[0]).group("ipv4")
    soft_assert(ipv4)
    command_set = (TimedCommand("ap", 30), RETURN, app_con_menu["config_net"], "2", ipv4, RETURN,
                   RETURN, RETURN, RETURN, RETURN, TimedCommand("Y", 30))
    output = appliance.appliance_console.run_commands(command_set, timeout=15)
    soft_assert("failed" not in output[-1])

    ipv6 = re.search(IPv6_REGEX, old_result[0]).group("ipv6")
    soft_assert(ipv6)
    command_set = ("ap", RETURN, app_con_menu["config_net"], "3", ipv6, RETURN, RETURN, RETURN,
                   RETURN, RETURN, TimedCommand("Y", 30))
    output = appliance.appliance_console.run_commands(command_set, timeout=15)
    soft_assert("failed" not in output[-1])

    hostname = fauxfactory.gen_alphanumeric(start="test", length=20).lower()
    command_set = (TimedCommand("ap", 30), RETURN, app_con_menu["config_net"], "5",
                   hostname, RETURN)
    appliance.appliance_console.run_commands(command_set, timeout=15)

    appliance.evmserverd.restart()

    command_set = ("ap", RETURN)
    new_result = appliance.appliance_console.run_commands(command_set, timeout=30)
    logger.info('"ap" command output after restart EVM service:%s', new_result)

    command_set = "ip a"
    ip_a_ret = appliance.ssh_client.run_command(command_set)
    soft_assert(ip_a_ret.success)
    ip_a_output = ip_a_ret.output.split("\n")
    logger.info('"ip a" command output:%s', ip_a_output)

    soft_assert(
        re.search(f"IPv4 Address: +{ipv4}", new_result[0]),
        (f"New {ipv4} IPV4 is not found on console appliance "),
    )
    soft_assert(
        [True for line in ip_a_output if ipv4 in line and "dynamic" not in line],
        (f'New {ipv4} IPV4 Changes are not reflected in "ip a" output.'),
    )

    soft_assert(
        re.search(f"IPv6 Address: +{ipv6}", new_result[0]),
        (f"New {ipv6} IPV6 is not found on console appliance"),
    )

    soft_assert(
        [True for line in ip_a_output if ipv6 in line and "dynamic" not in line],
        (f'New {ipv6} IPV6 Changes are not reflected in "ip a" output'),
    )

    soft_assert(
        [True for line in new_result[0].split("\n") if hostname in line],
        (f"New {hostname} hostname is not found on console appliance"),
    )

    # Testing hostname and ipv4
    command_set = (TimedCommand("ap", 30), RETURN, app_con_menu["config_net"], "4", hostname)
    out = appliance.appliance_console.run_commands(command_set, timeout=15)
    soft_assert("Success!" in out[-1], f"Unable to verify {hostname} Hostname")

    command_set = (TimedCommand("ap", 30), RETURN, app_con_menu["config_net"], "4", ipv4)
    out = appliance.appliance_console.run_commands(command_set, timeout=15)
    soft_assert("Success!" in out[-1], f"Unable to verify {ipv4} ipv4 ip")


@pytest.mark.tier(1)
def test_appliance_console_network_conf_negative(temp_appliance_preconfig_modscope):
    """
    test network configuration error with invalid settings

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. RETURN clears info screen.
            3. '1' configure network.
            4.  '1' Set DHCP Network Configuration
            5. provide invalid input for IPv4 network
            6. provide invalid input for IPv6 network
            7. 4) Test Network Configuration
            8. enter invalid ipv4
            9. enter invalid hostname
            10. 5) Set Hostname
            11. enter incorrect hostname
        expectedResults:
            1.
            2.
            3.
            4.
            5. verify response
            6. verify response
            7.
            8. verify response
            9. verify response
            10.
            11. verify response
    """
    appliance = temp_appliance_preconfig_modscope
    dhcp_invalid_input = "jdn3e3"
    command_set = ("ap", RETURN, "1", "1", dhcp_invalid_input)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert 'Please enter "yes" or "no".' in result[-1], (
        "Not getting error message for invalid error for dhcp IPV4")

    command_set = ("ap", RETURN, "1", "1", "Y", dhcp_invalid_input)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert 'Please enter "yes" or "no".' in result[-1], (
        "Not getting error message for invalid error for dhcp IPV6")

    invalid_hostname = fauxfactory.gen_alphanumeric(start="1test_", length=10)
    # TODO(BZ-1785257) remove this condition once this BZ got fixed
    if not BZ(1785257, forced_streams=['5.10', "5.11"]).blocks:
        command_set = ("ap", RETURN, "1", "4", invalid_hostname)
        result = appliance.appliance_console.run_commands(command_set, timeout=30)
        assert "Please provide a valid Hostname or IP Address." in result[-1], (
            "Not getting error message for invalid error for IPV6")

        command_set = ("ap", RETURN, "1", "5", invalid_hostname)
        appliance.appliance_console.run_commands(command_set, timeout=30)

        command_set = ("ap", RETURN)
        result = appliance.appliance_console.run_commands(command_set, timeout=30)
        logger.info('"ap" command output:%s' % result)

        assert [i for i in result if invalid_hostname in result] == [], (
            "Should not able to set incorrect hostname")


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1337525])
def test_appliance_console_vmdb_httpd(temp_appliance_preconfig_funcscope):
    """
    check that httpd starts after restarting vmdb

    Bugzilla:
        1337525

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/12h
        testSteps:
            1. Stop the EVM service
            2. press "ap"
            3. press any key to continue
            4. Press "7" for "Configure Database"
            5. Press "4" for "Reset Configured Database"
            6. Press "Y" for confirmation
            7. Enter Region Number
            8. Start EVM service
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7. Check "Database reset successfully" message
            8. UI should be up and running

    """
    appliance = temp_appliance_preconfig_funcscope

    # Stopping the EVM service
    command_set = ("ap", RETURN, app_con_menu["stop_evm"], TimedCommand("Y", 120))
    appliance.appliance_console.run_commands(command_set, timeout=30)

    command_set = ("ap", RETURN, app_con_menu["config_db"], "4", "Y", TimedCommand("99", 300))
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "Database reset successfully" in result[-1], "DB reset failed"

    # Starting the EVM service
    command_set = ("ap", RETURN, app_con_menu["start_evm"], TimedCommand("Y", 120))
    appliance.appliance_console.run_commands(command_set, timeout=30)
    appliance.wait_for_miq_ready()


@pytest.mark.tier(2)
def test_appliance_console_shutdown(temp_appliance_preconfig_modscope):
    """
    test shutting down the appliance

    Polarion:
        assignee: dgaikwad
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
    appliance = temp_appliance_preconfig_modscope
    command_set = ("ap", RETURN, app_con_menu["showdown_app"], "Y")
    appliance.appliance_console.run_commands(command_set, timeout=40)
    wait_for(lambda: appliance.ssh_client.connected,
             timeout=600,
             fail_condition=True,
             message='Wait for shutdown',
             delay=5)


@pytest.mark.tier(1)
def test_appliance_console_static_ip_negative(temp_appliance_preconfig_modscope):
    """
    test error on invalid static ip

    Polarion:
        assignee: dgaikwad
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
            6. '3' Set IPv6 Static Network Configuration
            7. Set invalid IPv6 address.
        expectedResults:
            1.
            2.
            3.
            4.
            5. Confirm network failure.
            6.
            7. Confirm network failure.
    """
    appliance = temp_appliance_preconfig_modscope
    command_set = ("ap", RETURN)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    logger.info('"ap" command output before test run:%s' % result)
    first_console_screen = result[0].split("\n")
    original_ipv4 = re.match(IPv4_REGEX, "".join([i for i in first_console_screen
                                                  if "IPv4 Address:" in i]).strip()).group(2)
    assert original_ipv4
    invalid_ipv4 = original_ipv4 + ".0"
    command_set = ("ap", RETURN, "1", "2", invalid_ipv4)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "Please provide a valid IP Address." in result[-1]

    original_ipv6 = re.match(IPv6_REGEX, "".join([i for i in first_console_screen
                                                  if "IPv6 Address:" in i]).strip()).group(2)
    assert original_ipv6
    invalid_ipv6 = original_ipv6 + ":11"
    command_set = ("ap", RETURN, "1", "3", invalid_ipv6)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "Please provide a valid IP Address." in result[-1]

    command_set = ("ap", RETURN)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    logger.info('"ap" command output after test:%s' % result)
    first_console_screen = result[0].split("\n")

    assert [i for i in first_console_screen if "IPv4 Address:" in i and original_ipv4 in i] != [], (
        f"old {original_ipv4} IPV4 is not found on console appliance ")

    assert [i for i in first_console_screen if "IPv6 Address:" in i and original_ipv6 in i] != [], (
        f"old {original_ipv6} IPV6 is not found on console appliance")


@test_requirements.ha_proxy
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
        assignee: jhenner
        casecomponent: HAProxy
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
        assignee: dgaikwad
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


@pytest.mark.tier(2)
def test_appliance_console_restore_db_network_negative(temp_appliance_preconfig_funcscope):
    """
    test restoring database with invalid connection settings

    Polarion:
        assignee: dgaikwad
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
    appliance = temp_appliance_preconfig_funcscope
    stop_evm_command = ("ap", RETURN, app_con_menu["stop_evm"], "Y", RETURN)
    appliance.appliance_console.run_commands(stop_evm_command, timeout=30)
    invalid_db_restore_location = "nfs://host.mydomain.com/exported/my_exported_folder/db.backup"
    command_set = ("ap", RETURN, app_con_menu["restore_db_from_bak"], "2",
                   invalid_db_restore_location, "Y")
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "Database restore failed." in result[-1]


@pytest.mark.tier(1)
def test_appliance_console_extend_storage_negative(appliance):
    """
    test extending storage with no additional partition

    Polarion:
        assignee: dgaikwad
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
    command_set = ("ap", RETURN, "11")
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "/dev/vd" not in result[-1], ("extra disks are not present.")


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1439348])
@pytest.mark.parametrize("ip_version_menu", [("2"), ("3")], ids=["ipv4", "ipv6"])
def test_appliance_console_static_dns(temp_appliance_preconfig_long, secondary_dns,
                                      ip_version_menu):
    """
    test setting secondary dns and check it"s saved as the new default

    Bugzilla:
        1439348

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. configure static ipv4
            2. stop and start EVM service
            3. reconfigure static ipv4
            4. configure static ipv6
            5. stop and start EVM service
            6. reconfigure static ipv6
        expectedResults:
            1.
            2.  check evm service status while stop and start
            3. check default secondary DNS is listed or not while entering  DNS
            4.
            5. check evm service status while stop and start
            6. check default secondary DNS is listed or not while entering  DNS
    """
    appliance = temp_appliance_preconfig_long
    command_set = ("ap", RETURN, app_con_menu["config_net"], ip_version_menu, RETURN, RETURN,
                   RETURN, RETURN, secondary_dns, RETURN, TimedCommand("Y", 120))
    appliance.appliance_console.run_commands(command_set, timeout=30)

    def _stop_start_evmserverd(appliance):
        command_set = ("ap", RETURN, app_con_menu["stop_evm"], "Y")
        appliance.appliance_console.run_commands(command_set, timeout=30)
        wait_for(lambda: appliance.evmserverd.running,
                 delay=10,
                 timeout=300,
                 fail_condition=True,
                 message='Waiting to stop EVM services',
                 fail_func=appliance.evmserverd.running
                 )

        command_set = ("ap", RETURN, app_con_menu["start_evm"], "Y")
        appliance.appliance_console.run_commands(command_set, timeout=30)
        appliance.evmserverd.wait_for_running()

    _stop_start_evmserverd(appliance)
    command_set = ("ap", RETURN, app_con_menu["config_net"], ip_version_menu, RETURN,
                   RETURN, RETURN, RETURN)
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert secondary_dns in result[-1], "Default secondary DNS not found while re-configuring IP"


@pytest.mark.tier(2)
def test_appliance_console_apache_reload_log_rotate(appliance):
    """
    Check that apache is not reloaded twice after log rotations.

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        initialEstimate: 1/12h
        startsin: 5.10
        testtype: structural
        testSteps:
            1. execute command 'cat  /etc/logrotate.d/miq_logs.conf'
        expectedResults:
            1. "bin/apache reload"  content should not be in output
    """
    command = "cat /etc/logrotate.d/miq_logs.conf"
    result = appliance.ssh_client.run_command(command)
    assert "bin/apache reload" not in result.output


@pytest.mark.tier(1)
def test_appliance_console_key_fetch_negative(temp_appliance_preconfig_funcscope):
    """
    test fetching key from fake remote host

    Polarion:
        assignee: dgaikwad
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
    appliance = temp_appliance_preconfig_funcscope
    invalid_ip = fauxfactory.gen_ipaddr()
    command_set = ("ap", RETURN, app_con_menu["gen_custom_encry_key"], "Y", "2", invalid_ip,
                   conf.credentials['default']['username'], conf.credentials['default']['password'],
                   TimedCommand(RETURN, 180))
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "Failed to fetch key" in result[-1], (
        "Overriding Encryption Key should fail when we enter invalid IP address")


@pytest.mark.manual("manualonly")
@pytest.mark.tier(1)
def test_appliance_console_negative():
    """
    test launching appliance_console without a network attached

    Bugzilla:
        1439345

    Polarion:
        assignee: dgaikwad
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


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[BZ(1753687)])
def test_ap_failed_dbconfig_status(temp_appliance_preconfig_funcscope):
    """ Test failed DB config command returns non-zero status.

    Polarion:
        assignee: mnadeem
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. Logged in into AP
            2. Make the command to fail "opt/rh/cfme-gemset/bin/appliance_console_cli -i -b /dev/sdb
               -S -d ${db_name} -U ${db_root} -p '${db_pass}'"
            3. Check command execution status "echo $?".
        expectedResults:
            1.
            2.
            3. The command "echo $?" should be non-zero
    """
    appliance = temp_appliance_preconfig_funcscope
    command = ("/opt/rh/cfme-gemset/bin/appliance_console_cli -i -b /dev/sdz -S"
               " -d ${db_name} -U ${db_root} -p '${db_pass}'")
    result = appliance.ssh_client.run_command(command, timeout=30)
    assert not result.success, ('DB configuration should fail because used disk "/dev/sdz" '
                                'which will not be available')


@pytest.mark.tier(0)
@pytest.mark.meta(automates=[1625377])
def test_appliance_console_vmdb_log_negative(temp_appliance_preconfig_funcscope):
    """
      test to verify database configuration logs on failure

    Bugzilla:
      1625377

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        testSteps:
            1. 'ap' launches appliance_console.
            2. press any key to continue
            3. press "7" to "Configure Database"
            4. press "3" tp "Join Region in External Database"
            5. enter the invalid DB hostname
            6. enter the port number
            7. enter the DB name
            8. enter the user name
            9. enter the password
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
            9. wait and verify "Validated failed with error" error message on appliance console
             and "could not connect to serve" error message in the appliance_console.log file
      """
    appliance = temp_appliance_preconfig_funcscope
    # Creating appliance_console.log file because initially it is not created by default
    appliance.ssh_client.run_command("touch /var/www/miq/vmdb/log/appliance_console.log")

    ap_console_tail = LogValidator('/var/www/miq/vmdb/log/appliance_console.log',
                           matched_patterns=['.*ERROR.*could not connect to serve.*'],
                           hostname=appliance.hostname)
    ap_console_tail.start_monitoring()

    command_set = ("ap", RETURN, app_con_menu["config_db"], "3", "XXX.XXX.XXX.XXX", RETURN,
                   RETURN, RETURN, TimedCommand(conf.credentials['default']['password'], 300)
                   )
    result = appliance.appliance_console.run_commands(command_set, timeout=30)
    assert "Validated failed with error" in result[-1], "Database Configuration is not failed"

    ap_console_tail.validate(wait="60s")


@pytest.mark.meta(automates=[1670138])
@pytest.mark.meta(blockers=[BZ(1670138, forced_streams=["5.10"])])
def test_appliance_overwrite_ssl_ipa(unconfigured_appliance, freeipa_provider):
    """test to check ssl modifying or not  when it install from freeipa server

    Bugzilla:
        1670138
    Polarion:
        caseimportance: high
        initialEstimate: 1/8h
        assignee: dgaikwad
        casecomponent: Appliance
        testSteps:
            1. appliance_console_cli --region=1 --internal --username=<username>
            --password=<password> --key --dbdisk=/dev/vdb
            2. appliance_console_cli \
                --ipaserver=<freeipa_server> \
                --ipaprincipal=<ipaprincipal> \
                --ipapassword=<ipapassword> \
                --iparealm=<iparealm>
            3. appliance_console_cli --ca=ipa --http-cert
        expectedResults:
            1.
            2.
            3. content should be modified from var/www/miq/vmdb/certs/server.cer and
            /var/www/miq/vmdb/certs/server.cer.key files after executing all 3 steps
    """
    appliance = unconfigured_appliance
    server_cer_command = "cat /var/www/miq/vmdb/certs/server.cer"
    server_cer_key_cmd = "cat /var/www/miq/vmdb/certs/server.cer.key"

    result = appliance.ssh_client.run_command(server_cer_command)
    assert result.success
    server_cer_op = result.output

    result = appliance.ssh_client.run_command(server_cer_key_cmd)
    assert result.success
    server_cer_key_op = result.output
    command = (f"appliance_console_cli --region=1 --internal "
               f"--username={credentials['database']['username']} "
               f"--password={credentials['database']['password']} "
               f"--key --dbdisk=/dev/vdb")
    result = appliance.ssh_client.run_command(command)
    assert result.success

    command = (f"appliance_console_cli --ipaserver={freeipa_provider.host1} "
               f"--ipaprincipal={freeipa_provider.ipaprincipal}"
               f" --ipapassword={freeipa_provider.bind_password}")
    result = appliance.ssh_client.run_command(command)
    assert result.success

    command = "appliance_console_cli --ca=ipa --http-cert"
    result = appliance.ssh_client.run_command(command)
    assert result.success

    result = appliance.ssh_client.run_command(server_cer_command)
    assert result.success
    assert server_cer_op != result.output

    result = appliance.ssh_client.run_command(server_cer_key_cmd)
    assert result.success
    assert server_cer_key_op != result.output


@pytest.mark.tier(0)
@pytest.mark.meta(coverage=[1720223])
@pytest.mark.manual("manualonly")
def test_appliance_console_logfile_config_reboot():
    """
        test to verify logfiles disk
    Bugzilla:
      1720223

    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        initialEstimate: 1/4h
        testSteps:
            1. get appliance with extra disk
            2. set "logfile configuration"
            3. set "Harden Appliance Using SCAP Configuration"
            4. reboot appliance
            5. use "df -h" command and check result
        expectedResults:
            1.
            2.
            3.
            4.
            5. logfiles should use new disk
      """
    pass


@pytest.mark.tier(0)
@pytest.mark.meta(automates=[1790995])
def test_appliance_console_menubar(appliance):
    """
    There should not be error on menubar on appliance console
    Bugzilla:
        1790995
    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: critical
        initialEstimate: 1/3h
        testSteps:
            1. execute command on shell "ap"
            2. press any key
            3. check console
        expectedResults:
            1.
            2.
            3. "translation missing: en.advanced_settings.timezone" should not be displayed
    """
    with SSHExpect(appliance) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.expect('Choose the advanced setting: ', timeout=60)
        with pytest.raises(SSHExpectTimeoutError):
            interaction.expect('translation missing: ', timeout=60)


@pytest.mark.manual
@pytest.mark.tier(0)
@pytest.mark.meta(coverage=[1625377])
def test_appliance_console_db_fail_log():
    """
    Error information gets logged to appliance_console.log on db configuration failure
    Bugzilla:
        1625377
    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        caseimportance: low
        initialEstimate: 1/3h
        caseposneg: negative
        testSteps:
            1. Execute "ap" command on shell
            2. press any key
            3. select "configure database"
            4. select "Join Region in External Database"
            5. enter invalid database name
        expectedResults:
            1.
            2.
            3.
            4.
            5. Error information gets logged to appliance_console.log
    """
    pass
