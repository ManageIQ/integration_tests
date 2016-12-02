# -*- coding: utf-8 -*-
import fauxfactory
from time import sleep

from cfme.configure.configuration import (
    DatabaseAuthSetting, ExternalAuthSetting, get_ntp_servers, set_ntp_servers)
from cfme.login import login_admin, logout
from utils.browser import ensure_browser_open
from utils.conf import credentials
from utils.ssh import SSHClient
from utils import appliance
from utils.path import conf_path


def disable_external_auth(auth_mode):
    if 'ipa' in auth_mode:
        disable_external_auth_ipa()
    elif 'openldap' in auth_mode:
        disable_external_auth_openldap()
    else:
        raise Exception("'auth_mode' is not within the expected values for ext_auth, "
                        "ipa or openldap..")


def setup_external_auth_ipa(**data):
    """Sets up the appliance for an external authentication with IPA.

    Keywords:
        get_groups: Get User Groups from External Authentication (httpd).
        ipaserver: IPA server address.
        iparealm: Realm.
        credentials: Key of the credential in credentials.yaml
    """
    connect_kwargs = {
        'username': credentials['host_default']['username'],
        'password': credentials['host_default']['password'],
        'hostname': data['ipaserver'],
    }
    appliance_name = 'cfmeappliance{}'.format(fauxfactory.gen_alpha(7).lower())
    appliance_address = appliance.IPAppliance().address
    appliance_fqdn = '{}.{}'.format(appliance_name, data['iparealm'].lower())
    ipaserver_ssh = SSHClient(**connect_kwargs)
    ipaserver_ssh.run_command('cp /etc/hosts /etc/hosts_bak')
    ipaserver_ssh.run_command("sed -i -r '/^{}/d' /etc/hosts".format(appliance_address))
    command = 'echo "{}\t{}" >> /etc/hosts'.format(appliance_address, appliance_fqdn)
    ipaserver_ssh.run_command(command)
    ipaserver_ssh.close()
    ssh = SSHClient()
    assert ssh.run_command('appliance_console_cli --host {}'.format(appliance_fqdn))
    ensure_browser_open()
    login_admin()
    if data["ipaserver"] not in get_ntp_servers():
        set_ntp_servers(data["ipaserver"])
        sleep(120)
    auth = ExternalAuthSetting(get_groups=data.pop("get_groups", False))
    auth.setup()
    creds = credentials.get(data.pop("credentials"), {})
    data.update(**creds)
    assert ssh.run_command(
        "appliance_console_cli --ipaserver {ipaserver} --iparealm {iparealm} "
        "--ipaprincipal {principal} --ipapassword {password}".format(**data)
    )
    login_admin()


def setup_external_auth_openldap(**data):
    """Sets up the appliance for an external authentication with OpenLdap.

    Keywords:
        get_groups: Get User Groups from External Authentication (httpd).
        ipaserver: IPA server address.
        iparealm: Realm.
        credentials: Key of the credential in credentials.yaml
    """
    connect_kwargs = {
        'username': credentials['host_default']['username'],
        'password': credentials['host_default']['password'],
        'hostname': data['ipaddress'],
    }
    appliance_obj = appliance.IPAppliance()
    appliance_name = 'cfmeappliance{}'.format(fauxfactory.gen_alpha(7).lower())
    appliance_address = appliance_obj.address
    appliance_fqdn = '{}.{}'.format(appliance_name, data['domain_name'])
    ldapserver_ssh = SSHClient(**connect_kwargs)
    # updating the /etc/hosts is a workaround due to the
    # https://bugzilla.redhat.com/show_bug.cgi?id=1360928
    command = 'echo "{}\t{}" >> /etc/hosts'.format(appliance_address, appliance_fqdn)
    ldapserver_ssh.run_command(command)
    ldapserver_ssh.get_file(remote_file=data['cert_filepath'],
                            local_path=conf_path.strpath)
    ldapserver_ssh.close()
    ensure_browser_open()
    login_admin()
    auth = ExternalAuthSetting(get_groups=data.pop("get_groups", True))
    auth.setup()
    appliance_obj.configure_appliance_for_openldap_ext_auth(appliance_fqdn)
    logout()


def disable_external_auth_ipa():
    """Unconfigure external auth."""
    ssh = SSHClient()
    ensure_browser_open()
    login_admin()
    auth = DatabaseAuthSetting()
    auth.update()
    assert ssh.run_command("appliance_console_cli --uninstall-ipa")
    appliance.IPAppliance().wait_for_web_ui()
    logout()


def disable_external_auth_openldap():
    auth = DatabaseAuthSetting()
    auth.update()
    sssd_conf = '/etc/sssd/sssd.conf'
    httpd_auth = '/etc/pam.d/httpd-auth'
    manageiq_remoteuser = '/etc/httpd/conf.d/manageiq-remote-user.conf'
    manageiq_ext_auth = '/etc/httpd/conf.d/manageiq-external-auth.conf'
    command = 'rm -rf {} && rm -rf {} && rm -rf {} && rm -rf {}'.format(
        sssd_conf, httpd_auth, manageiq_ext_auth, manageiq_remoteuser)
    ssh = SSHClient()
    assert ssh.run_command(command)
    ssh.run_command('systemctl restart evmserverd')
    appliance.IPAppliance().wait_for_web_ui()
    logout()
