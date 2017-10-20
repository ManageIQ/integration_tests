# -*- coding: utf-8 -*-
import fauxfactory
from time import sleep

from cfme.utils.browser import ensure_browser_open
from cfme.utils.conf import credentials
from cfme.utils.ssh import SSHClient
from cfme.utils.appliance import get_or_create_current_appliance
from cfme.utils.path import conf_path

# TODO move these into appliance


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
    current_appliance = get_or_create_current_appliance()
    appliance_name = 'cfmeappliance{}'.format(fauxfactory.gen_alpha(7).lower())
    appliance_address = current_appliance.address
    appliance_fqdn = '{}.{}'.format(appliance_name, data['iparealm'].lower())
    with SSHClient(**connect_kwargs) as ipaserver_ssh:
        ipaserver_ssh.run_command('cp /etc/hosts /etc/hosts_bak')
        ipaserver_ssh.run_command("sed -i -r '/^{}/d' /etc/hosts".format(appliance_address))
        command = 'echo "{}\t{}" >> /etc/hosts'.format(appliance_address, appliance_fqdn)
        ipaserver_ssh.run_command(command)
    with current_appliance.ssh_client as ssh:
        result = ssh.run_command('appliance_console_cli --host {}'.format(appliance_fqdn)).success
        if not current_appliance.is_pod:
            assert result
        else:
            # appliance_console_cli fails when calls hostnamectl --host. it seems docker issue
            # raise BZ ?
            assert str(ssh.run_command('hostname')).rstrip() == appliance_fqdn

        ensure_browser_open()
        current_appliance.server.login_admin()

        if data["ipaserver"] not in (
                current_appliance.server.settings.ntp_servers_values):
            current_appliance.server.settings.update_ntp_servers(
                {'ntp_server_1': data["ipaserver"]})
            sleep(120)
        current_appliance.server.authentication.set_auth_mode(
            mode='external', get_groups=data.pop("get_groups", False)
        )
        creds = credentials.get(data.pop("credentials"), {})
        data.update(**creds)
        assert ssh.run_command(
            "appliance_console_cli --ipaserver {ipaserver} --iparealm {iparealm} "
            "--ipaprincipal {principal} --ipapassword {password}".format(**data)
        )
    current_appliance.server.login_admin()


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
    current_appliance = get_or_create_current_appliance()
    appliance_name = 'cfmeappliance{}'.format(fauxfactory.gen_alpha(7).lower())
    appliance_address = current_appliance.address
    appliance_fqdn = '{}.{}'.format(appliance_name, data['domain_name'])
    with SSHClient(**connect_kwargs) as ldapserver_ssh:
        # updating the /etc/hosts is a workaround due to the
        # https://bugzilla.redhat.com/show_bug.cgi?id=1360928
        command = 'echo "{}\t{}" >> /etc/hosts'.format(appliance_address, appliance_fqdn)
        ldapserver_ssh.run_command(command)
        ldapserver_ssh.get_file(remote_file=data['cert_filepath'],
                                local_path=conf_path.strpath)
    ensure_browser_open()
    current_appliance.server.login_admin()
    current_appliance.server.authentication.set_auth_mode(
        mode='external', get_groups=data.pop("get_groups", True)
    )
    current_appliance.configure_appliance_for_openldap_ext_auth(appliance_fqdn)
    current_appliance.server.logout()


def disable_external_auth_ipa():
    """Unconfigure external auth."""
    current_appliance = get_or_create_current_appliance()
    with current_appliance.ssh_client as ssh:
        ensure_browser_open()
        current_appliance.server.login_admin()
        current_appliance.server.authentication.set_auth_mode()
        assert ssh.run_command("appliance_console_cli --uninstall-ipa")
        current_appliance.wait_for_web_ui()
    current_appliance.server.logout()


def disable_external_auth_openldap():
    current_appliance = get_or_create_current_appliance()
    current_appliance.server.authentication.set_auth_mode()
    sssd_conf = '/etc/sssd/sssd.conf'
    httpd_auth = '/etc/pam.d/httpd-auth'
    manageiq_remoteuser = '/etc/httpd/conf.d/manageiq-remote-user.conf'
    manageiq_ext_auth = '/etc/httpd/conf.d/manageiq-external-auth.conf'
    command = 'rm -rf {} && rm -rf {} && rm -rf {} && rm -rf {}'.format(
        sssd_conf, httpd_auth, manageiq_ext_auth, manageiq_remoteuser)
    with current_appliance.ssh_client as ssh:
        assert ssh.run_command(command)
        ssh.run_command('systemctl restart evmserverd')
        get_or_create_current_appliance().wait_for_web_ui()
    current_appliance.server.logout()
