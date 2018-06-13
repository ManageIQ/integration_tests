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


@pytest.mark.uncollectif(lambda appliance: appliance.is_pod)
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


def test_appliance_console_set_hostname(appliance, restore_hostname):
    """'ap' launch appliance_console, '' clear info screen, '1' loads network settings, '5' gives
    access to set hostname, 'hostname' sets new hostname."""

    hostname = 'test.example.com'
    command_set = ('ap', '', '1', '5', hostname,)
    appliance.appliance_console.run_commands(command_set)

    def is_hostname_set(appliance):
        assert appliance.ssh_client.run_command("hostname -f | grep {hostname}"
            .format(hostname=hostname))
    wait_for(is_hostname_set, func_args=[appliance])
    result = appliance.ssh_client.run_command("hostname -f")
    assert result.success
    assert result.output.strip() == hostname


@pytest.mark.parametrize('timezone', tzs, ids=[tz.name for tz in tzs])
def test_appliance_console_set_timezone(timezone, temp_appliance_preconfig_modscope):
    """'ap' launch appliance_console, '' clear info screen, '2' set timezone, 'opt' select
    region, 'timezone' selects zone, 'y' confirm slection, '' finish."""
    command_set = ('ap', '', '2') + timezone[1] + ('y', '')
    temp_appliance_preconfig_modscope.appliance_console.run_commands(command_set)

    temp_appliance_preconfig_modscope.appliance_console.timezone_check(timezone)


def test_appliance_console_datetime(temp_appliance_preconfig_funcscope):
    """Grab fresh appliance and set time and date through appliance_console and check result"""
    app = temp_appliance_preconfig_funcscope
    command_set = ('ap', '', '3', 'y', '2020-10-20', '09:58:00', 'y', '')
    app.appliance_console.run_commands(command_set)

    def date_changed():
        return app.ssh_client.run_command("date +%F-%T | grep 2020-10-20-10:00").success
    wait_for(date_changed)


@pytest.mark.uncollectif(
    lambda appliance: appliance.version < '5.9' or appliance.version <= '5.9.3')
def test_appliance_console_db_maintenance_hourly(appliance_with_preset_time):
    """Test database hourly re-indexing through appliance console"""
    app = appliance_with_preset_time
    command_set = ('ap', '', '7', 'y', 'n', '')
    app.appliance_console.run_commands(command_set)

    def maintenance_run():
        return app.ssh_client.run_command(
            "grep REINDEX /var/www/miq/vmdb/log/hourly_continuous_pg_maint_stdout.log").success

    wait_for(maintenance_run, timeout=300)


@pytest.mark.uncollectif(lambda appliance: appliance.version >= '5.9.3.1',
    reason="Feature removed in latest 5.9.3")
@pytest.mark.parametrize('period', [
    ['hourly'],
    ['daily', '10'],
    ['weekly', '10', '2'],
    ['monthly', '10', '20']
], ids=['hour', 'day', 'week', 'month'])
def test_appliance_console_db_maintenance_periodic(period, appliance_with_preset_time):
    """Tests full vacuums on database through appliance console"""
    app = appliance_with_preset_time
    command_set = ['ap', '', '7', 'n', 'y']
    command_set.extend(period)
    app.appliance_console.run_commands(command_set)

    def maintenance_run():
        return app.ssh_client.run_command(
            "grep 'periodic vacuum full completed' "
            "/var/www/miq/vmdb/log/hourly_continuous_pg_maint_stdout.log"
        ).success

    wait_for(maintenance_run, timeout=300)


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
    mon = '9' if unconfigured_appliances[0].version < '5.9.3.1' else '8'
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
    command_set = ('ap', '', mon, TimedCommand('1', 30), '')
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
    opt = '10' if unconfigured_appliance.version < '5.9.3.1' else '9'
    command_set = ('ap', '', opt, '1', 'y', '')
    unconfigured_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended():
        assert unconfigured_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended)


def test_appliance_console_ipa(ipa_crud, configured_appliance):
    """'ap' launches appliance_console, '' clears info screen, '11' setup IPA,
    + wait 40 secs and '' finish."""

    setup_ipa = '11' if configured_appliance.version < '5.9.3.1' else '10'
    command_set = ('ap', RETURN, setup_ipa,
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
    command_set = ('ap', RETURN, setup_ipa, TimedCommand('y', 40), TimedCommand('n', 5))
    configured_appliance.appliance_console.run_commands(command_set)
    wait_for(lambda: not configured_appliance.sssd.running)


@pytest.mark.parametrize('auth_type', ext_auth_options, ids=[opt.name for opt in ext_auth_options])
def test_appliance_console_external_auth(auth_type, app_creds, ipa_crud, configured_appliance):
    """'ap' launches appliance_console, '' clears info screen, '12/15' change ext auth options,
    'auth_type' auth type to change, '4' apply changes."""
    # TODO this depends on the auth_type options being disabled when the test is run
    # TODO it assumes that first switch is to true, then false.

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type.option)],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['sshpass'])
    evm_tail.fix_before_start()
    ext_auth = '12' if configured_appliance.version < '5.9.3.1' else '11'
    command_set = ('ap', '', ext_auth, auth_type.index, '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type.option)],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['sshpass'])

    evm_tail.fix_before_start()
    command_set = ('ap', '', ext_auth, auth_type.index, '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


def test_appliance_console_external_auth_all(app_creds, ipa_crud, configured_appliance):
    """'ap' launches appliance_console, '' clears info screen, '12/15' change ext auth options,
    'auth_type' auth type to change, '4' apply changes."""

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to true.*',
                                              '.*saml_enabled to true.*',
                                              '.*local_login_disabled to true.*'],
                            hostname=configured_appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    ext_auth = '12' if configured_appliance.version < '5.9.3.1' else '11'
    command_set = ('ap', '', ext_auth, '1', '2', '3', '4')
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
    command_set = ('ap', '', ext_auth, '1', '2', '3', '4')
    configured_appliance.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


def test_appliance_console_scap(temp_appliance_preconfig, soft_assert):
    """'ap' launches appliance_console, '' clears info screen, '14' Hardens appliance using SCAP
    configuration, '' complete."""

    opt = '14' if temp_appliance_preconfig.version < '5.9.3.1' else '13'
    command_set = ('ap', '', opt, '')
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
