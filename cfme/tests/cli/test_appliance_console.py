from fixtures.pytest_store import store
import pytest
from wait_for import wait_for
from utils import version
from utils.log_validator import LogValidator

# from utils.conf import cfme_data, credentials

# def test_black_console_static_ip
# def test_black_console_dhcp


def test_black_console_set_hostname(request):
    channel = store.current_appliance.ssh_client.invoke_shell()
    stdin = channel.makefile('wb')
    if store.current_appliance.version >= "5.8":
        stdin.write("ap \n 1 \n 4 \n test.example.com \n \n")
    else:
        stdin.write("ap \n 4 \n test.example.com \n \n")
    return_code, output = store.current_appliance.ssh_client.run_command(
        "hostname -f")
    assert output.strip() == 'test.example.com'
    assert return_code == 0


# def test_black_console_set_timezone(request):
#     client = store.current_appliance.ssh_client
#     channel = client.invoke_shell()
#     stdin = channel.makefile('wb')
#     stdin.write("ap \n 5 \n 1 \n 1 \n y \n \n")
#     return_code, output = store.current_appliance.ssh_client.run_command(
#         "ap | grep Africa/Abidjan")
#     assert return_code == 0


# def test_black_console_datetime
# def test_black_console_restore_db_local
# def test_black_console_restore_db_nfs
# def test_black_console_restore_db_samba


def test_black_console_internal_db(request, app_creds, temp_appliance_unconfig_funcscope):
    pwd = app_creds['password']
    client = temp_appliance_unconfig_funcscope.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        stdin.write("ap \n 5 \n 1 \n 1 \n 1 \n n \n 0 \n {} \n {} \n \n".format(pwd, pwd))
    else:
        stdin.write("ap \n 8 \n 1 \n 1 \n 1 \n n \n 0 \n {} \n {} \n \n".format(pwd, pwd))
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


def test_black_console_internal_db_reset(request, app_creds, temp_appliance_preconfig_funcscope):
    client = temp_appliance_preconfig_funcscope.ssh_client
    client.run_command('systemctl stop evmserverd')
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if temp_appliance_preconfig_funcscope.version >= "5.8":
        stdin.write("ap \n 5 \n 4 \n y \n 1 \n \n")
    else:
        stdin.write("ap \n 8 \n 4 \n y \n 1 \n \n")
    temp_appliance_preconfig_funcscope.wait_for_evm_service()
    temp_appliance_preconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_dedicated_db(temp_appliance_unconfig_funcscope, app_creds):
    pwd = app_creds['password']
    client = temp_appliance_unconfig_funcscope.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if temp_appliance_unconfig_funcscope.version >= "5.8":
        stdin.write("ap \n 5 \n 1 \n 1 \n 1 \n y \n {} \n {} \n \n".format(pwd, pwd))
    else:
        stdin.write("ap \n 8 \n 1 \n 1 \n 1 \n y \n {} \n {} \n \n".format(pwd, pwd))
    wait_for(temp_appliance_unconfig_funcscope.is_dedicated_db_active,
        func_args=[temp_appliance_unconfig_funcscope])


def test_black_console_external_db(request, temp_appliance_unconfig_funcscope, app_creds):
    appliance_ip = store.current_appliance.address
    pwd = app_creds['password']
    client = temp_appliance_unconfig_funcscope.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if temp_appliance_unconfig_funcscope >= "5.8":
        stdin.write("ap \n 5 \n 2 \n {appliance_ip} \n \n {pwd} \n \n 3 \n {appliance_ip} \n \n \n "
            "{pwd} \n {pwd} \n \n".format(appliance_ip=appliance_ip, pwd=pwd))
    else:
        stdin.write("ap \n 8 \n 2 \n {appliance_ip} \n \n {pwd} \n \n 3 \n {appliance_ip} \n \n \n "
            "{pwd} \n {pwd} \n \n".format(appliance_ip=appliance_ip, pwd=pwd))
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_black_console_external_db_create(request, app_creds, dedicated_db,
        temp_appliance_unconfig_funcscope):
    ip = dedicated_db.address
    pwd = app_creds['password']
    client = temp_appliance_unconfig_funcscope.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if temp_appliance_unconfig_funcscope >= "5.8":
        stdin.write("ap \n 5 \n 1 \n 1 \n 2 \n 0 \n y \n {ip} \n \n \n {pwd} \n {pwd} \n \n"
            .format(ip=ip, pwd=pwd))
    else:
        stdin.write("ap \n 8 \n 1 \n 1 \n 2 \n 0 \n y \n {ip} \n \n \n {pwd} \n {pwd} \n \n"
            .format(ip=ip, pwd=pwd))
    temp_appliance_unconfig_funcscope.wait_for_evm_service()
    temp_appliance_unconfig_funcscope.wait_for_web_ui()


# def test_black_console_extend_storage(request, fqdn_appliance):
#     client = fqdn_appliance.ssh_client
#     channel = client.invoke_shell()
#     stdin = channel.makefile('wb')
#     stdin.write("ap \n 13 \n 1 \n y \n \n")

#     def is_storage_extended(fqdn_appliance):
#         return_code, output = store.current_appliance.ssh_client.run_command(
#             "df -h | grep /var/www/miq_tmp")
#         assert return_code == 0
#     wait_for(is_storage_extended, func_args=[fqdn_appliance])


def test_black_console_ipa(request, fqdn_appliance, ipa_creds):
    client = fqdn_appliance.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if fqdn_appliance.version >= "5.8":
        stdin.write("ap \n 10 \n {hostname} \n {domain} \n \n {username} \n {password} \n y \n \n")
    else:
        stdin.write("ap \n 14 \n {hostname} \n {domain} \n \n {username} \n {password} \n y \n \n")

    def is_sssd_running(fqdn_appliance):
        assert fqdn_appliance.ssh_client.run_command("systemctl status sssd | grep running")
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
    client = ipa_crud.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if ipa_crud.version >= "5.8":
        stdin.write("ap \n 11 \n {} \n 4 \n".format(auth_type[1]))
    else:
        stdin.write("ap \n 15 \n {} \n 4 \n".format(auth_type[1]))
    evm_tail.validate_logs()

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*{} to false.*'.format(auth_type[0])],
                            hostname=ipa_crud.address,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])

    evm_tail.fix_before_start()
    client = ipa_crud.ssh_client
    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    if ipa_crud.version >= "5.8":
        stdin.write("ap \n 11 \n {} \n 4 \n".format(auth_type[1]))
    else:
        stdin.write("ap \n 15 \n {} \n 4 \n".format(auth_type[1]))
    evm_tail.validate_logs()


# def test_black_console_generate_key(request, temp_appliance_unconfig_funcscope):
#     time = temp_appliance_unconfig_funcscope.current_time  # figure this out
#     date = temp_appliance_unconfig_funcscope.current_date  # figure this out
#     client = temp_appliance_unconfig_funcscope.ssh_client
#     channel = client.invoke_shell()
#     stdin = channel.makefile('wb')
#     stdin.write("ap \n 16 \n y \n 1 \n \n")
#     return_code, output = temp_appliance_unconfig_funcscope.ssh_client.run_command(
#         "cat /var/www/miq/vmdb/certs/v2_key | grep ':created: {date} {time}'"
#         .format(date=date, time=time))
#     assert return_code == 0


# def test_black_console_generate_fetch_key(request, temp_appliance_unconfig_funcscope, app_creds):
#     ip = temp_appliance_unconfig_funcscope.addresss
#     pwd = app_creds['password']
#     key = temp_appliance_unconfig_funcscope.v2_key  # figure this out md5 the 2 files
#     client = temp_appliance_unconfig_funcscope.ssh_client
#     channel = client.invoke_shell()
#     stdin = channel.makefile('wb')
#     stdin.write("ap \n 16 \n y \n 2 \n {ip} \n \n {pwd} \n \n \n".format(ip=ip, pwd=pwd))
#     return_code, output = temp_appliance_unconfig_funcscope.ssh_client.run_command(
#         "cat /var/www/miq/vmdb/certs/v2_key | grep '{key}'".format(key=key))
#     assert return_code == 0
