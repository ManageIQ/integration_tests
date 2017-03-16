import pytest
from wait_for import wait_for
from utils import version
from utils.log_validator import LogValidator


def test_black_console_set_hostname(request, appliance):
    hostname = 'test.com'
    if appliance.version >= "5.8":
        commands = ['ap', '\n', '1', '4', '{hostname}'.format(hostname=hostname)]
    else:
        commands = ['ap', '\n', '4', '{hostname}'.format(hostname=hostname)]
    appliance.appliance_console.run_commands(commands)

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
        commands = ['ap\n', '\n', '5\n', '1\n', '1\n', 'y\n', '1\n', 'n\n', '0\n',
            '{pwd}\n'.format(pwd=pwd), ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    else:
        commands = ['ap\n', '\n', '8\n', '1\n', '1\n', 'y\n', '1\n', 'n\n', '0\n',
            '{pwd}\n'.format(pwd=pwd), ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(commands)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_internal_db_reset(request, app_creds, temp_appliance_preconfig_funcscope):
    temp_appliance_preconfig_funcscope.ssh_client.run_command('systemctl stop evmserverd')
    if temp_appliance_preconfig_funcscope.version >= "5.8":
        commands = ['ap\n', '\n', '5\n', '4\n', 'y\n', ('1\n', 90), '\n', '\n', '15\n', 'y\n']
    else:
        commands = ['ap\n', '\n', '8\n', '4\n', 'y\n', ('1\n', 90), '\n', '\n', '19\n', 'y\n']
    temp_appliance_preconfig_funcscope.appliance_console.run_commands(commands)
    temp_appliance_preconfig_funcscope.wait_for_evm_service()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_dedicated_db(temp_appliance_unconfig_funcscope, app_creds):
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        commands = ['ap\n', '\n', '5\n', '1\n', '1\n', '1\n', 'y\n',
            '{pwd}\n'.format(pwd=pwd), ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    else:
        commands = ['ap\n', '\n', '8\n', '1\n', '1\n', '1\n', 'y\n',
            '{pwd}\n'.format(pwd=pwd), ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(commands)
    wait_for(temp_appliance_unconfig_funcscope.is_dedicated_db_active)


def test_black_console_external_db(
        request, temp_appliance_unconfig_funcscope, app_creds, appliance):
    ip = appliance.address
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        commands = ['ap\n', '\n', '5\n', '2\n', '{ip}\n'.format(ip=ip), '\n',
            '{pwd}\n'.format(pwd=pwd), '\n', '3\n', '{ip}\n'.format(ip=ip), '\n', '\n',
            '{pwd}\n'.format(pwd=pwd), ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    else:
        commands = ['ap\n', '\n', '8\n', '2\n', '{ip}\n'.format(ip=ip), '\n',
            '{pwd}\n'.format(pwd=pwd), '\n', '3\n', '{ip}\n'.format(ip=ip), '\n', '\n',
            '{pwd}\n'.format(pwd=pwd), ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(commands)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_external_db_create(request, app_creds, dedicated_db_appliance,
        temp_appliance_unconfig_funcscope):
    ip = dedicated_db_appliance.address
    pwd = app_creds['password']
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        commands = ['ap\n', '\n', '5\n', '1\n', '1\n', '2\n', '0\n', 'y\n',
            '{ip}\n'.format(ip=ip), '\n', '\n', '{pwd}\n'.format(pwd=pwd),
            ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    else:
        commands = ['ap\n', '\n', '8\n', '1\n', '1\n', '2\n', '0\n', 'y\n',
            '{ip}\n'.format(ip=ip), '\n', '\n', '{pwd}\n'.format(pwd=pwd),
            ('{pwd}\n'.format(pwd=pwd), 45), '\n']
    temp_appliance_unconfig_funcscope.appliance_console.run_commands(commands)
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_extend_storage(request, fqdn_appliance):
    if fqdn_appliance.version >= "5.8":
        commands = ['ap\n', '\n', '10\n', '1\n', 'y\n', '\n']
    else:
        commands = ['ap\n', '\n', '13\n', '1\n', 'y\n', '\n']
    fqdn_appliance.appliance_console.run_commands(commands)

    def is_storage_extended(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("df -h | grep /var/www/miq_tmp")
    wait_for(is_storage_extended, func_args=[fqdn_appliance])


def test_black_console_ipa(request, ipa_creds, fqdn_appliance):
    if fqdn_appliance.version >= "5.8":
        commands = ['ap\n', '\n', '11\n',
            '{hostname}\n'.format(hostname=ipa_creds['hostname']),
            '{domain}\n'.format(domain=ipa_creds['domain']), '\n',
            '{username}\n'.format(username=ipa_creds['username']),
            '{password}\n'.format(password=ipa_creds['password']), ('y\n', 40), '\n']
    else:
        commands = ['ap\n', '\n', '14\n',
            '{hostname}\n'.format(hostname=ipa_creds['hostname']),
            '{domain}\n'.format(domain=ipa_creds['domain']), '\n',
            '{username}\n'.format(username=ipa_creds['username']),
            '{password}\n'.format(password=ipa_creds['password']), ('y\n', 40), '\n']
    fqdn_appliance.appliance_console.run_commands(commands)

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
        commands = ['ap\n', '\n', '12\n', '{auth}\n'.format(auth=auth_type[1]), '4\n']
    else:
        commands = ['ap\n', '\n', '15\n', '{auth}\n'.format(auth=auth_type[1]), '4\n']
    ipa_crud.appliance_console.run_commands(commands)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type[0])],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    if ipa_crud.version >= "5.8":
        commands = ['ap\n', '\n', '12\n', '{auth}\n'.format(auth=auth_type[1]), '4\n']
    else:
        commands = ['ap\n', '\n', '15\n', '{auth}\n'.format(auth=auth_type[1]), '4\n']
    ipa_crud.appliance_console.run_commands(commands)
    evm_tail.validate_logs()
