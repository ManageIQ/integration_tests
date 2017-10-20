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
def test_black_console(appliance):
    """'ap | tee /tmp/opt.txt)' saves stdout to file, 'ap' launch appliance_console."""
    command_set = ('ap | tee -a /tmp/opt.txt', 'ap')
    appliance.appliance_console.run_commands(command_set)
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Virtual Appliance'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Database:'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Version:'"
                                            .format(appliance.product_name))


def test_black_console_set_hostname(appliance):
    """'ap' launch appliance_console, '' clear info screen, '1' loads network settings, '4/5' gives
    access to set hostname, 'hostname' sets new hostname."""

    hostname = 'test.example.com'
    opt = ('1', '5') if appliance.version >= "5.8" else ('4',)

    command_set = ('ap', '',) + opt + (hostname,)
    appliance.appliance_console.run_commands(command_set)

    def is_hostname_set(appliance):
        assert appliance.ssh_client.run_command("hostname -f | grep {hostname}"
            .format(hostname=hostname))
    wait_for(is_hostname_set, func_args=[appliance])
    return_code, output = appliance.ssh_client.run_command("hostname -f")
    assert output.strip() == hostname
    assert return_code == 0


@pytest.mark.parametrize('timezone', tzs, ids=[tz.name for tz in tzs])
def test_black_console_set_timezone(request, timezone, temp_appliance_preconfig_modscope):
    """'ap' launch appliance_console, '' clear info screen, '2/5' set timezone, 'opt' select
    region, 'timezone' selects zone, 'y' confirm slection, '' finish."""
    opt = '2' if temp_appliance_preconfig_modscope.version >= "5.8" else '5'
    command_set = ('ap', '', opt) + timezone[1] + ('y', '')
    temp_appliance_preconfig_modscope.appliance_console.run_commands(command_set)

    temp_appliance_preconfig_modscope.appliance_console.timezone_check(timezone)


def test_black_console_internal_db(app_creds, temp_appliance_unconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'n' don't create dedicated db, '0'
    db region number, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    pwd = app_creds['password']
    opt = '5' if temp_appliance_unconfig_funcscope.version >= "5.8" else '8'
    command_set = ('ap', '', opt, '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_internal_db_reset(app_creds, temp_appliance_preconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '4' reset db, 'y'
    confirm db reset, '1' db region number + wait 360 secs, '' continue"""

    opt = '5' if temp_appliance_preconfig_funcscope.version >= "5.8" else '8'
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    command_set = ('ap', '', opt, '4', 'y', TimedCommand('1', 360), '')
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl start evmserverd')
    temp_appliance_preconfig_funcscope.wait_for_evm_service()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


def test_black_console_dedicated_db(temp_appliance_unconfig_funcscope, app_creds):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'y' create dedicated db, 'pwd'
    db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    pwd = app_creds['password']
    opt = '5' if temp_appliance_unconfig_funcscope.version >= "5.8" else '8'
    command_set = ('ap', '', opt, '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    wait_for(lambda: temp_appliance_unconfig_funcscope.db.is_dedicated_active)


def test_black_console_external_db(temp_appliance_unconfig_funcscope, app_creds, appliance):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '2' fetch v2_key,
    'ip' address to fetch from, '' default username, 'pwd' db password, '' default v2_key location,
    '3' join external region, 'port' ip and port of joining region, '' use defult db name, ''
    default username, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    ip = appliance.address
    pwd = app_creds['password']
    opt = '5' if temp_appliance_unconfig_funcscope.version >= "5.8" else '8'
    port = (ip, '') if temp_appliance_unconfig_funcscope.version >= "5.8" else (ip,)
    command_set = ('ap', '', opt, '2', ip, '', pwd, '', '3') + port + ('', '',
        pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_external_db_create(app_creds, dedicated_db_appliance,
        temp_appliance_unconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' create v2_key,
    '2' create region in external db, '0' db region number, 'y' confirm create region in external db
    'port' ip and port for dedicated db, '' use defult db name, '' default username, 'pwd' db
    password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    ip = dedicated_db_appliance.address
    pwd = app_creds['password']
    opt = '5' if temp_appliance_unconfig_funcscope.version >= "5.8" else '8'
    port = (ip, '') if temp_appliance_unconfig_funcscope.version >= "5.8" else (ip,)
    command_set = ('ap', '', opt, '1', '2', '0', 'y') + port + ('', '', pwd,
        TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_extend_storage(fqdn_appliance):
    """'ap' launches appliance_console, '' clears info screen, '10/13' extend storage, '1' select
    disk, 'y' confirm configuration and '' complete."""

    opt = '10' if fqdn_appliance.version >= "5.8" else '13'
    command_set = ('ap', '', opt, '1', 'y', '')
    fqdn_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended, func_args=[fqdn_appliance])


@pytest.mark.skip('No IPA servers currently available')
def test_black_console_ipa(ipa_creds, fqdn_appliance):
    """'ap' launches appliance_console, '' clears info screen, '11/14' setup IPA, 'y' confirm setup
    + wait 40 secs and '' finish."""

    opt = '11' if fqdn_appliance.version >= "5.8" else '14'
    command_set = ('ap', '', opt, ipa_creds['hostname'], ipa_creds['domain'], '',
        ipa_creds['username'], ipa_creds['password'], TimedCommand('y', 40), '')
    fqdn_appliance.appliance_console.run_commands(command_set)

    def is_sssd_running(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("systemctl status sssd | grep running")
    wait_for(is_sssd_running, func_args=[fqdn_appliance])
    return_code, output = fqdn_appliance.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0


@pytest.mark.skip('No IPA servers currently available')
@pytest.mark.parametrize('auth_type', [
    LoginOption('sso', 'sso_enabled', '1'),
    LoginOption('saml', 'saml_enabled', '2'),
    LoginOption('local_login', 'local_login_disabled', '3')
], ids=['sso', 'saml', 'local_login'])
def test_black_console_external_auth(auth_type, app_creds, ipa_crud):
    """'ap' launches appliance_console, '' clears info screen, '12/15' change ext auth options,
    'auth_type' auth type to change, '4' apply changes."""

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type.option)],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    opt = '12' if ipa_crud.version >= "5.8" else '15'
    command_set = ('ap', '', opt, auth_type.index, '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type.option)],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    opt = '12' if ipa_crud.version >= "5.8" else '15'
    command_set = ('ap', '', opt, auth_type.index, '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


@pytest.mark.skip('No IPA servers currently available')
def test_black_console_external_auth_all(app_creds, ipa_crud):
    """'ap' launches appliance_console, '' clears info screen, '12/15' change ext auth options,
    'auth_type' auth type to change, '4' apply changes."""

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to true.*', '.*saml_enabled to true.*',
                                '.*local_login_disabled to true.*'],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    opt = '12' if ipa_crud.version >= "5.8" else '15'
    command_set = ('ap', '', opt, '1', '2', '3', '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to false.*',
                                '.*saml_enabled to false.*', '.*local_login_disabled to false.*'],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    opt = '12' if ipa_crud.version >= "5.8" else '15'
    command_set = ('ap', '', opt, '1', '2', '3', '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


def test_black_console_scap(temp_appliance_preconfig, soft_assert):
    """'ap' launches appliance_console, '' clears info screen, '14/17' Hardens appliance using SCAP
    configuration, '' complete."""

    opt = '14' if temp_appliance_preconfig.version >= "5.8" else '17'
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
