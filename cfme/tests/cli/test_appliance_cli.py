from fixtures.pytest_store import store


def test_set_hostname(request):
    store.current_appliance.ap_cli.set_hostname('test.example.com')
    return_code, output = store.current_appliance.ssh_client.run_command(
        "hostname -f")
    assert output.strip() == 'test.example.com'
    assert return_code == 0


def test_configure_appliance_internal_fetch_key(request, app_creds, appliance):
    app = appliance
    fetch_key_ip = store.current_appliance.address
    app.ap_cli.configure_appliance_internal_fetch_key(0, 'localhost',
        app_creds['username'], app_creds['password'], 'vmdb_production', fetch_key_ip,
        app_creds['sshlogin'], app_creds['sshpass'])
    app.wait_for_evm_service()
    app.wait_for_web_ui()


def test_ipa_crud(request, ipa_creds, fqdn_appliance):
    app = fqdn_appliance
    app.ap_cli.configure_ipa(ipa_creds['ipaserver'], ipa_creds['username'],
        ipa_creds['password'], ipa_creds['domain'], ipa_creds['realm'])
    assert app.ssh_client.run_command("systemctl status sssd | grep running")
    return_code, output = app.ssh_client.run_command(
        "cat /etc/ipa/default.conf | grep 'enable_ra = True'")
    assert return_code == 0
    app.ap_cli.uninstall_ipa_client()
    return_code, output = app.ssh_client.run_command(
        "cat /etc/ipa/default.conf")
    assert return_code != 0
