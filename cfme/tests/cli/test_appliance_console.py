import pytest
from collections import namedtuple
from wait_for import wait_for
from utils import version
from utils.log_validator import LogValidator
from utils.log import logger
from utils.path import data_path
import lxml.etree
import yaml

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
LoginOption = namedtuple('LoginOption', ['name', 'option', 'index'])


@pytest.mark.smoke
def test_black_console(appliance):
    """'exec > >(tee /tmp/opt.txt)' saves stdout to file, 'ap' launch appliance_console."""
    command_set = ('exec > >(tee /tmp/opt.txt)', 'ap')
    appliance.appliance_console.run_commands(command_set)
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Virtual Appliance'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Database:'"
                                            .format(appliance.product_name))
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep '{} Version:'"
                                            .format(appliance.product_name))


def test_black_console_set_hostname(appliance):
    """'ap' launch appliance_console, '' clear info screen, '1' loads network settings, '4' gives
    access to set hostname, 'hostname' sets new hostname."""

    hostname = 'test.example.com'
    if appliance.version >= "5.8":
        command_set = ('ap', '', '1', '5', hostname)
    else:
        command_set = ('ap', '', '4', hostname)
    appliance.appliance_console.run_commands(command_set)

    def is_hostname_set(appliance):
        assert appliance.ssh_client.run_command("hostname -f | grep {hostname}"
            .format(hostname=hostname))
    wait_for(is_hostname_set, func_args=[appliance])
    return_code, output = appliance.ssh_client.run_command("hostname -f")
    assert output.strip() == hostname
    assert return_code == 0


def test_black_console_internal_db(app_creds, temp_appliance_unconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'n' don't create dedicated db, '0'
    db region number, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 360), '')
    else:
        command_set = ('ap', '', '8', '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_internal_db_reset(app_creds, temp_appliance_preconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '4' reset db, 'y'
    confirm db reset, '1' db region number + wait 360 secs, '' continue, '' clear info screen,
    '15/19' start evm and 'y' confirm start."""

    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    if temp_appliance_preconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '4', 'y', TimedCommand('1', 360), '')
    else:
        command_set = ('ap', '', '8', '4', 'y', TimedCommand('1', 360), '')
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl start evmserverd')
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.wait_for_evm_service()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_dedicated_db(temp_appliance_unconfig_funcscope, app_creds):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' Creates v2_key,
    '1' selects internal db, 'y' continue, '1' use partition, 'y' create dedicated db, 'pwd'
    db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    else:
        command_set = ('ap', '', '8', '1', '1', 'y', '1', 'y', pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    wait_for(temp_appliance_unconfig_funcscope.is_dedicated_db_active)


def test_black_console_external_db(temp_appliance_unconfig_funcscope, app_creds, appliance):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '2' fetch v2_key,
    'ip' address to fetch from, '' default username, 'pwd' db password, '' default v2_key location,
    '3' join external region, 'ip' address of joining region, '' default port number, '' use defult
    db name, '' default username, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and
    '' finish."""

    ip = appliance.address
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '2', ip, '', pwd, '', '3', ip, '', '', '',
            pwd, TimedCommand(pwd, 360), '')
    else:
        command_set = ('ap', '', '8', '2', ip, '', pwd, '', '3', ip, '', '',
            pwd, TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_external_db_create(app_creds, dedicated_db_appliance,
        temp_appliance_unconfig_funcscope):
    """'ap' launch appliance_console, '' clear info screen, '5/8' setup db, '1' create v2_key,
    '2' create region in external db, '0' db region number, 'y' confirm create region in external db
    'ip' address of dedicated db, '' default port number, '' use defult db name, '' default
    username, 'pwd' db password, 'pwd' confirm db password + wait 360 secs and '' finish."""

    ip = dedicated_db_appliance.address
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '1', '2', '0', 'y', ip, '', '', '', pwd,
            TimedCommand(pwd, 360), '')
    else:
        command_set = ('ap', '', '8', '1', '2', '0', 'y', ip, '', '', pwd,
            TimedCommand(pwd, 360), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_extend_storage(fqdn_appliance):
    """'ap' launches appliance_console, '' clears info screen, '10/13' extend storage, '1' select
    disk, 'y' confirm configuration and '' complete."""

    if fqdn_appliance.version >= "5.8":
        command_set = ('ap', '', '10', '1', 'y', '')
    else:
        command_set = ('ap', '', '13', '1', 'y', '')
    fqdn_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended, func_args=[fqdn_appliance])


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_ipa(ipa_creds, fqdn_appliance):
    """'ap' launches appliance_console, '' clears info screen, '11/14' setup IPA, 'y' confirm setup
    + wait 40 secs and '' finish."""

    if fqdn_appliance.version >= "5.8":
        command_set = ('ap', '', '11', ipa_creds['hostname'], ipa_creds['domain'], '',
            ipa_creds['username'], ipa_creds['password'], TimedCommand('y', 40), '')
    else:
        command_set = ('ap', '', '14', ipa_creds['hostname'], ipa_creds['domain'], '',
            ipa_creds['username'], ipa_creds['password'], TimedCommand('y', 40), '')
    fqdn_appliance.appliance_console.run_commands(command_set)

    def is_sssd_running(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("systemctl status sssd | grep running")
    wait_for(is_sssd_running, func_args=[fqdn_appliance])
    return_code, output = fqdn_appliance.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
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
    if ipa_crud.version >= "5.8":
        command_set = ('ap', '', '12', auth_type.index, '4')
    else:
        command_set = ('ap', '', '15', auth_type.index, '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type.option)],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    if ipa_crud.version >= "5.8":
        command_set = ('ap', '', '12', auth_type.index, '4')
    else:
        command_set = ('ap', '', '15', auth_type.index, '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
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
    if ipa_crud.version >= "5.8":
        command_set = ('ap', '', '12', '1', '2', '3', '4')
    else:
        command_set = ('ap', '', '15', '1', '2', '3', '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*sso_enabled to false.*',
                                '.*saml_enabled to false.*', '.*local_login_disabled to false.*'],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    if ipa_crud.version >= "5.8":
        command_set = ('ap', '', '12', '1', '2', '3', '4')
    else:
        command_set = ('ap', '', '15', '1', '2', '3', '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()


def test_black_console_scap(temp_appliance_preconfig, soft_assert):
    """'ap' launches appliance_console, '' clears info screen, '14/17' Hardens appliance using SCAP
    configuration, '' complete."""

    if temp_appliance_preconfig.version >= "5.8":
        command_set = ('ap', '', '14', '')
    else:
        command_set = ('ap', '', '17', '')
    temp_appliance_preconfig.appliance_console.run_commands(command_set)

    temp_appliance_preconfig.ssh_client.put_file(
        data_path.join("cli", "scap.rb").strpath, '/tmp/scap.rb')
    temp_appliance_preconfig.ssh_client.run_command('cd /tmp/ && ruby /tmp/scap.rb')
    temp_appliance_preconfig.ssh_client.run_command('cd /tmp/ && ruby /tmp/scap.rb')
    temp_appliance_preconfig.ssh_client.get_file(
        '/tmp/scap-results.xccdf.xml', '/tmp/scap-results.xccdf.xml')
    temp_appliance_preconfig.ssh_client.get_file(
        '/var/www/miq/vmdb/gems/pending/appliance_console/config/scap_rules.yml',
        '/tmp/scap_rules.yml')    # Get the scap rules (moves on 5.8)

    with open('/tmp/scap_rules.yml') as f:
        yml = yaml.load(f.read())    # read file and PARSE as yaml (hows rules that should be run)
        rules = yml['rules']     # Pick the rules bit so we end up with a list of rules

    tree = lxml.etree.parse('/tmp/scap-results.xccdf.xml')    # load and PARSE the xml file
    root = tree.getroot()    # get the root level of the XML tree
    for rule in rules:    # iterate over rules storing each result as idref attribute (rule name)
        elements = root.findall(
            './/{{http://checklists.nist.gov/xccdf/1.1}}rule-result[@idref="{}"]'.format(rule))
        if elements:   # if we find any elements
            result = elements[0].findall('./{http://checklists.nist.gov/xccdf/1.1}result')
            if result:  # if we find a result element "result" tag, passed, failed, etc
                soft_assert(result == 'pass')
                logger.info("{}: {}".format(rule, result[0].text))  # result after the rule name
            else:  # don't find a result print we can't find result, should be an exception
                logger.info("{}: no result".format(rule))
        else:   # we didn't find a rule-result for the specific rule
            logger.info("{}: rule not found".format(rule))  # can't find the rule (update scap.rb)
