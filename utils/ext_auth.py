# -*- coding: utf-8 -*-
from time import sleep

from cfme.configure.configuration import (
    DatabaseAuthSetting, ExternalAuthSetting, get_ntp_servers, set_ntp_servers)
from cfme.login import login_admin, logout
from utils.browser import ensure_browser_open
from utils.conf import credentials
from utils.ssh import SSHClient
from utils import appliance


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
    import fauxfactory
    appliance_name = 'cfmeappliance'.format(fauxfactory.gen_alpha(7).lower())
    appliance_address = appliance.IPAppliance().address
    appliance_fqdn = '{}.{}'.format(appliance_name, data['iparealm'].lower())
    ipaserver_ssh = SSHClient(**connect_kwargs)
    # updating the /etc/hosts is a workaround due to the
    # https://bugzilla.redhat.com/show_bug.cgi?id=1360928
    command = 'echo "{}\t{}" >> /etc/hosts'.format(appliance_address, appliance_fqdn)
    ipaserver_ssh.run_command(command)
    ipaserver_ssh.close()
    ssh = SSHClient()
    rc, out = ssh.run_command('appliance_console_cli --host {}'.format(appliance_fqdn))
    assert rc == 0, out
    ssh.run_command('echo "127.0.0.1\t{}" > /etc/hosts'.format(appliance_fqdn))
    ensure_browser_open()
    login_admin()
    if data["ipaserver"] not in get_ntp_servers():
        set_ntp_servers(data["ipaserver"])
        sleep(120)
    auth = ExternalAuthSetting(get_groups=data.pop("get_groups", False))
    auth.setup()
    logout()
    creds = credentials.get(data.pop("credentials"), {})
    data.update(**creds)
    rc, out = ssh.run_command(
        "appliance_console_cli --ipaserver {ipaserver} --iparealm {iparealm} "
        "--ipaprincipal {principal} --ipapassword {password}".format(**data)
    )
    assert rc == 0, out
    assert "failed" not in out.lower(), "External auth setup failed:\n{}".format(out)
    login_admin()


def disable_external_auth_ipa():
    """Unconfigure external auth."""
    ssh = SSHClient()
    ensure_browser_open()
    login_admin()
    auth = DatabaseAuthSetting()
    auth.update()
    rc, out = ssh.run_command("appliance_console_cli --uninstall-ipa")
    assert rc == 0, out
