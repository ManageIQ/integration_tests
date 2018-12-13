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

pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason="cli isn't supported in pod appliance")
]

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
    LoginOption('local_login', 'local_login_disabled', '3')
]


@pytest.mark.rhel_testing
@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
@pytest.mark.smoke
@pytest.mark.tier(2)
def test_appliance_console(appliance):
    """'ap | tee /tmp/opt.txt)' saves stdout to file, 'ap' launch appliance_console.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/12h
    """
    command_set = ('ap | tee -a /tmp/opt.txt', 'ap')
    appliance.appliance_console.run_commands(command_set)
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
    2. '' clear info screen,
    3. '1' loads network settings,
    4. '5' gives access to set hostname,
    5. 'hostname' sets new hostname.

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: appl
        initialEstimate: 1/6h
    """

    hostname = 'test.example.com'
    command_set = ('ap', '', '1', '5', hostname,)
    configured_appliance.appliance_console.run_commands(command_set)

    def is_hostname_set(appliance):
        assert appliance.ssh_client.run_command("hostname -f | grep {hostname}"
            .format(hostname=hostname))
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
    2. '' clear info screen,
    3. '2' set timezone,
    4. 'opt' select region,
    5. 'timezone' selects zone,
    6. 'y' confirm slection,
    7. '' finish.

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: config
        initialEstimate: 1/6h
    """
    command_set = ('ap', '', '2') + timezone[1] + ('y', '')
    temp_appliance_preconfig_modscope.appliance_console.run_commands(command_set)

    temp_appliance_preconfig_modscope.appliance_console.timezone_check(timezone)


@pytest.mark.rhel_testing
@pytest.mark.tier(1)
def test_appliance_console_datetime(temp_appliance_preconfig_funcscope):
    """Grab fresh appliance and set time and date through appliance_console and check result

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: config
        initialEstimate: 1/6h
    """
    app = temp_appliance_preconfig_funcscope
    command_set = ('ap', '', '3', 'y', '2020-10-20', '09:58:00', 'y', '')
    app.appliance_console.run_commands(command_set)

    def date_changed():
        return app.ssh_client.run_command("date +%F-%T | grep 2020-10-20-10:00").success
    wait_for(date_changed)


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_internal_db(app_creds, unconfigured_appliance):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. '' clear info screen,
    3. '5' setup db,
    4. '1' Creates v2_key,
    5. '1' selects internal db,
    6. 'y' continue,
    7. '1' use partition,
    8. 'n' don't create dedicated db,
    9. '0' db region number,
    10. 'pwd' db password,
    11. 'pwd' confirm db password + wait 360 secs
    12. '' finish.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/4h
    """

    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 360), '')
    unconfigured_appliance.appliance_console.run_commands(command_set)
    unconfigured_appliance.evmserverd.wait_for_running()
    unconfigured_appliance.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_internal_db_reset(temp_appliance_preconfig_funcscope):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. '' clear info screen,
    3. '5' setup db,
    4. '4' reset db,
    5. 'y' confirm db reset,
    6. '1' db region number + wait 360 secs,
    7. '' continue

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: config
        initialEstimate: 1/4h
    """

    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    command_set = ('ap', '', '5', '4', 'y', TimedCommand('1', 360), '')
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl start evmserverd')
    temp_appliance_preconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_dedicated_db(unconfigured_appliance, app_creds):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. '' clear info screen,
    3. '5' setup db,
    4. '1' Creates v2_key,
    5. '1' selects internal db,
    6. 'y' continue,
    7. '1' use partition,
    8. 'y' create dedicated db,
    9. 'pwd' db password,
    10. 'pwd' confirm db password + wait 360 secs
    11. '' finish.

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: appl
        initialEstimate: 1/3h
        testtype: structural
    """

    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
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
        casecomponent: config
        initialEstimate: 1h
        testtype: structural
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
    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_web_ui()
    # Configure primary replication node
    command_set = ('ap', '', '6', '1', '1', '', '', pwd, pwd, app0_ip, 'y',
        TimedCommand('y', 60), '')
    apps[0].appliance_console.run_commands(command_set)
    # Configure secondary replication node
    if apps[0].version > '5.9':
        command_set = ('ap', '', '6', '2', '2', app0_ip, '', pwd, '', '1', '2', '', '', pwd, pwd,
                       app0_ip, app1_ip, 'y', TimedCommand('y', 60), '')
    else:
        command_set = ('ap', '', '6', '2', '1', '2', '', '', pwd, pwd, app0_ip, app1_ip, 'y',
                       TimedCommand('y', 60), '')
    apps[1].appliance_console.run_commands(command_set)
    # Configure automatic failover on EVM appliance
    command_set = ('ap', '', '8', TimedCommand('1', 30), '')
    apps[2].appliance_console.run_commands(command_set)

    def is_ha_monitor_started(appliance):
        return bool(appliance.ssh_client.run_command(
            "grep {} /var/www/miq/vmdb/config/failover_databases.yml".format(app1_ip)).success)
    wait_for(is_ha_monitor_started, func_args=[apps[2]], timeout=300, handle_exception=True)
    # Cause failover to occur
    result = apps[0].ssh_client.run_command('systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
    assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    def is_failover_started(appliance):
        return bool(appliance.ssh_client.run_command(
            "grep 'Starting to execute failover' /var/www/miq/vmdb/log/ha_admin.log").success)
    wait_for(is_failover_started, func_args=[apps[2]], timeout=450, handle_exception=True)
    apps[2].evmserverd.wait_for_running()
    apps[2].wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_external_db(temp_appliance_unconfig_funcscope, app_creds, appliance):
    """ Commands:
    1. 'ap' launch appliance_console,
    2. '' clear info screen,
    3. '5/8' setup db,
    4. '2' fetch v2_key,
    5. 'ip' address to fetch from,
    6. '' default username,
    7. 'pwd' db password,
    8. '' default v2_key location,
    9. '3' join external region,
    10. 'port' ip and port of joining region,
    11. '' use default db name,
    12. '' default username,
    13. 'pwd' db password,
    14. 'pwd' confirm db password + wait 360 secs
    15. '' finish.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/2h
        testtype: structural
    """

    ip = appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', '', '5', '2', ip, '', pwd, '', '3', ip, '', '', '',
        pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.evmserverd.wait_for_running()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_external_db_create(
        app_creds, dedicated_db_appliance, unconfigured_appliance_secondary):
    """
    1. 'ap' launch appliance_console,
    2. '' clear info screen,
    3. '5' setup db,
    4. '1'
    5. create v2_key,
    6. '2' create region in external db,
    7. '0' db region number,
    8. 'y' confirm create region in external db
    9. 'ip',
    10. '' ip and port for dedicated db,
    11. '' use default db name,
    12. '' default username,
    13. 'pwd' db  password,
    14. 'pwd' confirm db password + wait 360 secs,
    15. '' finish.

    Polarion:
        assignee: sbulage
        caseimportance: high
        casecomponent: appl
        initialEstimate: 1/3h
    """

    ip = dedicated_db_appliance.hostname
    pwd = app_creds['password']
    command_set = ('ap', '', '5', '1', '2', '0', 'y', ip, '', '', '', pwd,
        TimedCommand(pwd, 300), '')
    unconfigured_appliance_secondary.appliance_console.run_commands(command_set)
    unconfigured_appliance_secondary.evmserverd.wait_for_running()
    unconfigured_appliance_secondary.wait_for_web_ui()


@pytest.mark.tier(2)
def test_appliance_console_extend_storage(unconfigured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '9' extend storage,
    4. '1' select disk,
    5. 'y' confirm configuration,
    6. '' complete.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/4h
    """
    command_set = ('ap', '', '9', '1', 'y', '')
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended)


@pytest.mark.rhel_testing
def test_appliance_console_ipa(ipa_crud, configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '10' setup IPA, + wait 40 secs,
    4. '' finish.

    Polarion:
        assignee: sbulage
        caseimportance: high
        initialEstimate: None
    """

    command_set = ('ap', RETURN, '10',
                   ipa_crud.host1,
                   ipa_crud.ipadomain or RETURN,
                   ipa_crud.iparealm or RETURN,
                   ipa_crud.ipaprincipal or RETURN,
                   ipa_crud.bind_password,
                   TimedCommand('y', 40), RETURN)
    configured_appliance.appliance_console.run_commands(command_set)
    configured_appliance.sssd.wait_for_running()
    assert configured_appliance.ssh_client.run_command("cat /etc/ipa/default.conf |"
                                                       "grep 'enable_ra = True'")

    # Unconfigure to cleanup
    # When setup_ipa option selected, will prompt to unconfigure, then to proceed with new config
    command_set = ('ap', RETURN, '10', TimedCommand('y', 40), TimedCommand('n', 5))
    configured_appliance.appliance_console.run_commands(command_set)
    wait_for(lambda: not configured_appliance.sssd.running)


@pytest.mark.parametrize('auth_type', ext_auth_options, ids=[opt.name for opt in ext_auth_options])
def test_appliance_console_external_auth(auth_type, app_creds, ipa_crud, configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '11' change ext auth options,
    4. 'auth_type' auth type to change,
    5. '4' apply changes.

    Polarion:
        assignee: sbulage
        caseimportance: high
        initialEstimate: None
    """
    # TODO this depends on the auth_type options being disabled when the test is run
    # TODO it assumes that first switch is to true, then false.

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type.option)],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['sshpass'])
    evm_tail.fix_before_start()
    command_set = ('ap', '', '11', auth_type.index, '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type.option)],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['sshpass'])

    evm_tail.fix_before_start()
    command_set = ('ap', '', '11', auth_type.index, '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


def test_appliance_console_external_auth_all(app_creds, ipa_crud, configured_appliance):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '12/15' change ext auth options,
    4. 'auth_type' auth type to change,
    5. '4' apply changes.

    Polarion:
        assignee: sbulage
        caseimportance: high
        initialEstimate: None
    """

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to true.*',
                                              '.*saml_enabled to true.*',
                                              '.*local_login_disabled to true.*'],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    command_set = ('ap', '', '11', '1', '2', '3', '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to false.*',
                                              '.*saml_enabled to false.*',
                                              '.*local_login_disabled to false.*'],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    command_set = ('ap', '', '11', '1', '2', '3', '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
def test_appliance_console_scap(temp_appliance_preconfig, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '13' Hardens appliance using SCAP configuration,
    4. '' complete.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/3h
    """

    command_set = ('ap', '', '13', '')
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


@pytest.mark.tier(1)
def test_appliance_console_dhcp(unconfigured_appliance, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '1' configure network,
    4. '1' configure DHCP,
    5. 'y' confirm IPv4 configuration,
    6. 'y' IPv6 configuration.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/6h
    """
    command_set = ('ap', '', '1', '1', 'y', 'y')
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def appliance_is_connective():
        unconfigured_appliance.ssh_client.run_command("true")
    wait_for(appliance_is_connective, handle_exception=True, delay=1, timeout=30)

    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip a show dev eth0 | grep 'inet\s.*dynamic'"))
    soft_assert(unconfigured_appliance.ssh_client.run_command
        ("ip a show dev eth0 | grep 'inet6\s.*dynamic'"))


@pytest.mark.tier(1)
def test_appliance_console_static_ipv4(unconfigured_appliance, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '1' configure network,
    4. '2' configure static IPv4,
    5. '' confirm default IPv4 addr,
    6. '' confirm default netmask,
    7. '' confirm default gateway,
    8. '' confirm default primary DNS,
    9. '' confirm default secondary DNS,
    10. '' confirm default search order,
    11. 'y' apply static configuration.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: critical
        initialEstimate: 1/6h
    """
    command_set = ('ap', '', '1', '2', '', '', '', '', '', '', 'y')
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def appliance_is_connective():
        unconfigured_appliance.ssh_client.run_command("true")
    wait_for(appliance_is_connective, handle_exception=True, delay=1, timeout=30)

    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -4 a show dev eth0 | grep 'inet .*scope global eth0'"))
    soft_assert(unconfigured_appliance.ssh_client.run_command(
        "ip -4 r show dev eth0 | grep 'default via'"))


def test_appliance_console_static_ipv6(unconfigured_appliance, soft_assert):
    """ Commands:
    1. 'ap' launches appliance_console,
    2. '' clears info screen,
    3. '1' configure network,
    4. '3' configure static IPv6,
    5. '1::1' set IPv4 addr,
    6. '' set deafault prefix length,
    7. '1::f' set IPv6 gateway,
    8. '' confirm default primary DNS,
    9. '' confirm default secondary DNS,
    10. '' confirm default search order,
    11. 'y' apply static configuration.

    Polarion:
        assignee: sbulage
        caseimportance: high
        initialEstimate: None
    """
    command_set = ('ap', '', '1', '3', '1::1', '', '1::f', '', '', '', 'y')
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def appliance_is_connective():
        unconfigured_appliance.ssh_client.run_command("true")
    wait_for(appliance_is_connective, handle_exception=True, delay=1, timeout=30)

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
        casecomponent: config
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
        casecomponent: config
        initialEstimate: 1/2h
        setup: provision 3 appliances
               setup HA following https://mojo.redhat.com/docs/DOC-1097888
               (https://mojo.redhat.com/docs/DOC-1168738)
               check setup is working be accessing webui
        startsin: 5.8
        testSteps:
            1. Setup HA
        expectedResults:
            1. Confirm primary database server, application server is
               running and it can access the webui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_screen():
    """
    Test new screen package added to appliances. Should be able to run a
    task and switch terminal/screen within ssh to run other tasks
    simultaneously.
    Just type "screen" after logging in to ssh to start using it. Once you
    have screen running, "ctrl-a" intiates screen command "c" creates new
    screen, "n" switch to next screen., "p" for previous screen, "d"
    detach from screens (this takes you back to standard terminal) and run
    screen -r to resume using screen.

    Polarion:
        assignee: sbulage
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
        startsin: 5.9
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_restart():
    """
    test restarting the appliance

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_ha_dc_re_establish():
    """
    Test that upon re-connection of networks the repmgr process continues
    to replicate correctly to the disconnected node within DC2

    Polarion:
        assignee: sbulage
        casecomponent: config
        initialEstimate: 1/2h
        setup: Restore network connectivity between DC1 and DC2
        startsin: 5.8
        testSteps:
            1. Restore network connectivity between DC1 and DC2
        expectedResults:
            1. Confirm replication is working correctly
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_evm_stop():
    """
    test stopping the evm server process

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_evm_start():
    """
    test starting the evm server process

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_check_default_ip():
    """
    test ip settings, checking all the defaults are what is expected.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_ssl():
    """
    Test ssl connections to postgres database from other appliances.
    https://bugzilla.redhat.com/show_bug.cgi?id=1482697

    Polarion:
        assignee: sbulage
        casecomponent: config
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
        casecomponent: config
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
    https://bugzilla.redhat.com/show_bug.cgi?id=1438844

    Polarion:
        assignee: sbulage
        casecomponent: config
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
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_network_conf_negative():
    """
    test network configuration error with invalid settings

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_vmdb_httpd():
    """
    check that httpd starts after restarting vmdb
    https://bugzilla.redhat.com/show_bug.cgi?id=1337525

    Polarion:
        assignee: sbulage
        casecomponent: appl
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
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_static_ip_negative():
    """
    test error on invalid static ip

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
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

    Polarion:
        assignee: sbulage
        casecomponent: config
        initialEstimate: 1/2h
        setup: Failover to DC1 standby node, drop connections between DC"s, restore
               network connectivity between DC1 and DC2 manually kill DC1 current
               primary if its in a split brain scenario.
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_logfile():
    """
    Test configuring new log file disk volume.

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/6h
        setup: -provision new appliance with additional disk
               -ssh to appliance
               -run appliance_console
               -select option "Logfile Configuration"
               -configure disk
               -confirm new logfile disk is configured correctly
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_restore_db_network_negative():
    """
    test restoring database with invalid connection settings

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/3h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_packages():
    """
    Check that we no long use scl packages in cfme. We should not have an
    rh-ruby packages.

    Polarion:
        assignee: sbulage
        casecomponent: appl
        initialEstimate: 1/12h
        startsin: 5.10
        testtype: structural
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_appliance_console_cli_rh_registration():
    """
    Test RHSM registration through cli and check if changes are made
    within the ui

    Polarion:
        assignee: sbulage
        casecomponent: appl
        caseimportance: medium
        initialEstimate: 1/12h
        setup: Provision appliace
               ssh to it and run "subscription-manager register"
               check changes within the ui
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_extend_storage_negative():
    """
    test extending storage with no additional partition

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.9', '5.10')
def test_appliance_console_db_maintenance_periodic_unconfigure():
    """
    Test unconfiguring full vacums

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        endsin: 5.8
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "configure database maintenance"
               -say yes to "unconfigure Periodic Database Maintance"
               -wait for the set time
               -check that full vacums have stopped by checking log in
               "vmdb/log/hourly.........log" (all timescales are stored in the hourly
               log file)
        startsin: 5.7
        testSteps:
            1. unconfigure periodic maintenance
        expectedResults:
            1. full vacuums stop running
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_static_dns():
    """
    test setting secondary dns and check it"s saved as the new default
    https://bugzilla.redhat.com/show_bug.cgi?id=1439348

    Polarion:
        assignee: sbulage
        casecomponent: appl
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
        assignee: sbulage
        casecomponent: appl
        initialEstimate: 1/12h
        startsin: 5.10
        testtype: structural
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('5.9', '5.10')
def test_appliance_console_db_maintenance_hourly_unconfigure():
    """
    Test unconfiguring db maintenance for Hourly re-indexing of tables

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        endsin: 5.8
        initialEstimate: 1/6h
        setup: -ssh to appliance
               -run appliance_console
               -select option "configure database maintenance"
               -say yes to unconfigure hourly database maintenance (requires hourly
               db maintenance to already be configured)
               -wait 1 hour
               -check that maintenance is has stopped correctly by checking log in
               "vmdb/log/hourly.........log"
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_datetime_negative():
    """
    test setting invalid date/time

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_key_fetch_negative():
    """
    test fetching key from fake remote host

    Polarion:
        assignee: sbulage
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_appliance_console_negative():
    """
    test launching appliance_console without a network attached
    https://bugzilla.redhat.com/show_bug.cgi?id=1439345

    Polarion:
        assignee: sbulage
        casecomponent: appl
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/6h
    """
    pass
