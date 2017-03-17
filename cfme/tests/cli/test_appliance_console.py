import pytest
from collections import namedtuple
from wait_for import wait_for
from utils import version
from utils.log_validator import LogValidator

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])


@pytest.mark.smoke
def test_black_console(request, appliance):
    command_set = ('exec > >(tee /tmp/opt.txt)', 'ap', '')
    appliance.appliance_console.run_commands(command_set)
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep 'CFME Virtual Appliance'")
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep 'CFME Server:'")
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep 'CFME Database:'")
    assert appliance.ssh_client.run_command("cat /tmp/opt.txt | grep 'CFME Version:'")


def test_black_console_set_hostname(request, appliance):
    hostname = 'Elite-QE.redhat.com'
    if appliance.version >= "5.8":
        command_set = ('ap', '', '1', '4', hostname)
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


def test_black_console_internal_db(request, app_creds, temp_appliance_unconfig_funcscope):
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 45), '')
    else:
        command_set = ('ap', '', '8', '1', '1', 'y', '1', 'n', '0', pwd, TimedCommand(pwd, 45), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_internal_db_reset(request, app_creds, temp_appliance_preconfig_funcscope):
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    if temp_appliance_preconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '4', 'y', TimedCommand('1', 90), '', '', '15', 'y')
    else:
        command_set = ('ap', '', '8', '4', 'y', TimedCommand('1', 90), '', '', '19', 'y')
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_preconfig_funcscope.wait_for_evm_service()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_dedicated_db(temp_appliance_unconfig_funcscope, app_creds):
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '1', '1', '1', 'y', pwd, TimedCommand(pwd, 45), '')
    else:
        command_set = ('ap', '', '8', '1', '1', '1', 'y', pwd, TimedCommand(pwd, 45), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    wait_for(temp_appliance_unconfig_funcscope.is_dedicated_db_active)


def test_black_console_external_db(
        request, temp_appliance_unconfig_funcscope, app_creds, appliance):
    ip = appliance.address
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '2', ip, '', pwd, '', '3', ip, '', '',
            pwd, TimedCommand(pwd, 45), '')
    else:
        command_set = ('ap', '', '8', '2', ip, '', pwd, '', '3', ip, '', '',
            pwd, TimedCommand(pwd, 45), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_external_db_create(request, app_creds, dedicated_db_appliance,
        temp_appliance_unconfig_funcscope):
    ip = dedicated_db_appliance.address
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        command_set = ('ap', '', '5', '1', '1', '2', '0', 'y', ip, '', '', pwd,
            TimedCommand(pwd, 45), '')
    else:
        command_set = ('ap', '', '8', '1', '1', '2', '0', 'y', ip, '', '', pwd,
            TimedCommand(pwd, 45), '')
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(command_set)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_extend_storage(request, fqdn_appliance):
    if fqdn_appliance.version >= "5.8":
        command_set = ('ap', '', '10', '1', 'y', '')
    else:
        command_set = ('ap', '', '13', '1', 'y', '')
    fqdn_appliance.appliance_console.run_commands(command_set)

    def is_storage_extended(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended, func_args=[fqdn_appliance])


def test_black_console_ipa(request, ipa_creds, fqdn_appliance):
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


@pytest.mark.parametrize('auth_type', [('sso_enabled', '1'), ('saml_enabled', '2'),
    ('local_login_disabled', '3')], ids=['sso', 'saml', 'local_login'])
def test_black_console_external_auth(request, auth_type, app_creds, ipa_crud):
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type[0])],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    if ipa_crud.version >= "5.8":
        command_set = ('ap', '', '12', auth_type[1], '4')
    else:
        command_set = ('ap', '', '15', auth_type[1], '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type[0])],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    if ipa_crud.version >= "5.8":
        command_set = ('ap', '', '12', auth_type[1], '4')
    else:
        command_set = ('ap', '', '15', auth_type[1], '4')
    ipa_crud.appliance_console.run_commands(command_set)
    evm_tail.validate_logs()
