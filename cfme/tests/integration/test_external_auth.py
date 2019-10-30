import pytest
from gevent.timeout import Timeout

from cfme import test_requirements
from cfme.utils.auth import get_auth_crud

pytestmark = [test_requirements.auth]

# External auth specific test cases (e.g. freeipa)


@pytest.fixture
def freeipa_provider():
    # run this on freeipa03 as to not affect tests running on freeipa01
    auth_prov = get_auth_crud("freeipa03")
    # turn off ntpd
    cmd = auth_prov.ssh_client.run_command("systemctl stop ntpd")
    assert cmd.success
    yield auth_prov
    # turn ntpd back on
    cmd = auth_prov.ssh_client.run_command("systemctl start ntpd")
    assert cmd.success


@pytest.mark.tier(1)
def test_appliance_console_ipa_ntp(request, appliance, freeipa_provider):
    """
    Try to setup IPA on appliance when NTP daemon is stopped on server.

    Polarion:
        assignee: jdupuy
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/4h
        caseposneg: negative
        setup:
            1. Have IPA server configured and running
                - https://mojo.redhat.com/docs/DOC-1058778
        testSteps:
            1. ssh into IPA server stop NTP daemon
            2. ssh to appliance and try to setup IPA
                - appliance_console_cli --ipaserver <IPA_URL> --ipaprincipal <LOGIN>
                    --ipapassword <PASS> --ipadomain <DOMAIN> --iparealm <REALM>
        expectedResults:
            1. NTP daemon stopped
            2. Command should fail; setting up IPA unsuccessful
    """
    request.addfinalizer(appliance.disable_freeipa)

    # we expect configuration to fail because ntpd is off on freeipa03
    with pytest.raises((Timeout, AssertionError)):
        appliance.configure_freeipa(freeipa_provider)
