from store import current_appliance


def test_set_hostname(request):
    current_appliance.ap_cli.set_hostname()
    return_code, output = current_appliance.ssh.run_command(
        "cat /etc/hosts | grep test.example.com")
    assert return_code == 0


def test_configure_appliance(request):
    current_appliance.ap_cli.configure_appliance(region, internal, dbhostname, username,
    password, dbname, key, fetch_key, sshlogin, sshpass)
    return_code, output = (current_appliance.ssh.run_command(
        "systemctl status evmserverd | grep running"))
    assert return_code == 0

# do I still need two tests for configuring appliance now
# or one with all the options for setting up both?

# def test_configure_appliance_fetch_key(request):
#    current_appliance.ap_cli.configure_appliance_fetch_key(ip="")
#    return_code, output = (current_appliance.ssh.run_command
# ("systemctl status evmserverd | grep running"))
#    assert return_code == 0


def test_configure_ipa(request):
    current_appliance.ap_cli.configure_ipa(
    hostname="", domain="", realm="", username="", password="")
    return_code, output = (current_appliance.ssh.run_command(
        "systemctl status sssd | grep running"))
    assert return_code == 0
    return_code, output = (current_appliance.ssh.run_command(
        "cat /etc/ipa/default.conf | grep enable_ra = True"))
    assert return_code == 0


def test_uninstall_ipa(request):
    current_appliance.ap_cli.uninstall_ipa()
    return_code, output = (current_appliance.ssh.run_command("cat /etc/ipa/default.conf"))
    assert return_code == 0
