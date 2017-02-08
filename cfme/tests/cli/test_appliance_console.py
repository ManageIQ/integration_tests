from fixtures.pytest_store import store
from cfme.fixtures.cli import is_dedicated_db_active
import pytest
from wait_for import wait_for
from utils import version
from utils.log_validator import LogValidator
# from utils.conf import cfme_data, credentials


def is_storage_extended(fqdn_appliance):
    return_code, output = store.current_appliance.ssh_client.run_command(
        "df -h | grep /var/www/miq_tmp")
    assert return_code == 0


def is_sssd_running(fqdn_appliance):
    assert fqdn_appliance.ssh_client.run_command("systemctl status sssd | grep running")

# def test_black_console_static_ip
# def test_black_console_dhcp


def test_black_console_set_hostname(request):
    client = store.current_appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 4 \n test.example.com \n \n")
    return_code, output = store.current_appliance.ssh_client.run_command(
        "hostname -f")
    assert output.strip() == 'test.example.com'
    assert return_code == 0


def test_black_console_set_timezone(request):
    client = store.current_appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 5 \n 1 \n 1 \n y \n \n")
    return_code, output = store.current_appliance.ssh_client.run_command(
        "ap | grep Africa/Abidjan")
    assert return_code == 0


# def test_black_console_datetime
# def test_black_console_restore_db_local
# def test_black_console_restore_db_nfs
# def test_black_console_restore_db_samba


def test_black_console_internal_db(request, app_creds, appliance):
    pwd = app_creds['password']
    client = appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 8 \n 1 \n 1 \n 1 \n n \n 0 \n {} \n {} \n \n"
        .format(pwd, pwd))
    appliance.wait_for_evm_service()
    appliance.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_dedicated_db(appliance, app_creds):
    pwd = app_creds['password']
    client = appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 8 \n 1 \n 1 \n 1 \n y \n {} \n {} \n \n".format(pwd, pwd))
    wait_for(is_dedicated_db_active, func_args=[appliance])


def test_black_console_external_db(request, appliance, app_creds):
    appliance_ip = store.current_appliance.address
    pwd = app_creds['password']
    client = appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 8 \n 2 \n {appliance_ip} \n \n {pwd} \n \n 3 \n {appliance_ip} \n \n \n "
        "{pwd} \n {pwd} \n \n".format(appliance_ip=appliance_ip, pwd=pwd))
    appliance.wait_for_evm_service()
    appliance.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_external_db_create(request, app_creds, dedicated_db, appliance):
    ip = dedicated_db.address
    pwd = app_creds['password']
    client = appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 8 \n 1 \n 1 \n 2 \n 0 \n y \n {ip} \n \n \n {pwd} \n {pwd} \n \n"
        .format(ip=ip, pwd=pwd))
    appliance.wait_for_evm_service()
    appliance.wait_for_web_ui()


def test_black_console_extend_storage(request, fqdn_appliance):
    client = fqdn_appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 13 \n 1 \n y \n \n")
    wait_for(is_storage_extended, func_args=[fqdn_appliance])


def test_black_console_ipa(request, fqdn_appliance, ipa_creds):
    client = fqdn_appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 14 \n {hostname} \n {domain} \n \n {username} \n {password} \n y \n \n")
    wait_for(is_sssd_running, func_args=[fqdn_appliance])
    return_code, output = fqdn_appliance.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0


@pytest.mark.parametrize('auth_type', [('sso_enabled', '1'), ('saml_enabled', '2'),
    ('local_login_disabled', '3')], ids=['sso', 'saml', 'local_login'])
def test_black_console_external_auth(request, auth_type, ipa_crud, app_creds):
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to true.*'.format(auth_type[0])],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    command = "ap \n 15 \n {} \n 4 \n".format(auth_type[1])
    ipa_crud.ssh_client.run_command(command)
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type[0])],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    command2 = "ap \n 15 \n {} \n 4 \n".format(auth_type[1])
    ipa_crud.ssh_client.run_command(command2)
    evm_tail.validate_logs()


def test_black_console_generate_key(request, appliance):
    time = appliance.current_time  # figure this out
    date = appliance.current_date  # figure this out
    client = appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 16 \n y \n 1 \n \n")
    return_code, output = appliance.ssh_client.run_command(
        "cat /var/www/miq/vmdb/certs/v2_key | grep ':created: {date} {time}'"
        .format(date=date, time=time))
    assert return_code == 0


def test_black_console_generate_fetch_key(request, appliance, app_creds):
    ip = appliance.addresss
    pwd = app_creds['password']
    key = appliance.v2_key  # figure this out
    client = appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdin.write("ap \n 16 \n y \n 2 \n {ip} \n \n {pwd} \n \n \n".format(ip=ip, pwd=pwd))
    return_code, output = appliance.ssh_client.run_command(
        "cat /var/www/miq/vmdb/certs/v2_key | grep '{key}'".format(key=key))
    assert return_code == 0
