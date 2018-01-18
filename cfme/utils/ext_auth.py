# -*- coding: utf-8 -*-
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


def setup_external_auth_ipa(appliance, **data):
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
    appliance_address = appliance.hostname
    with SSHClient(**connect_kwargs) as ipaserver_ssh:
        assert ipaserver_ssh.run_command('cp /etc/hosts /etc/hosts_bak')
        assert ipaserver_ssh.run_command("sed -i -r '/^{}/d' /etc/hosts".format(appliance_address))
        assert ipaserver_ssh.run_command('echo "{}\t{}" >> /etc/hosts'
                                         .format(appliance_address, appliance.fqdn))
    with appliance.ssh_client as ssh:
        if appliance.is_pod:
            # appliance_console_cli fails when calls hostnamectl --host. it seems docker issue
            # raise BZ ?
            assert str(ssh.run_command('hostname')).rstrip() == appliance.fqdn

        ensure_browser_open()
        appliance.server.login_admin()
        data.update(**credentials.get(data.pop("credentials"), {}))
        data.pop('auth_mode', None)  # suppresses KeyError, don't need auth_mode, its external
        appliance.configure_freeipa(**data)

        appliance.server.login_admin()


def setup_external_auth_openldap(appliance, **data):
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
    with SSHClient(**connect_kwargs) as ldapserver_ssh:
        ldapserver_ssh.get_file(remote_file=data['cert_filepath'],
                                local_path=conf_path.strpath)
    ensure_browser_open()
    appliance.server.login_admin()
    appliance.server.authentication.configure_auth(
        auth_mode='external', get_groups=data.pop("get_groups", True)
    )
    appliance.configure_openldap()
    appliance.server.logout()


def disable_external_auth_ipa():
    """Unconfigure external auth."""
    current_appliance = get_or_create_current_appliance()
    with current_appliance.ssh_client as ssh:
        ensure_browser_open()
        current_appliance.server.login_admin()
        current_appliance.server.authentication.configure_auth()
        assert ssh.run_command("appliance_console_cli --uninstall-ipa")
        current_appliance.wait_for_web_ui()
    current_appliance.server.logout()


def disable_external_auth_openldap():
    current_appliance = get_or_create_current_appliance()
    current_appliance.server.authentication.configure_auth()
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
