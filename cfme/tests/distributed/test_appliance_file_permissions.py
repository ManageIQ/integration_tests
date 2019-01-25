import pytest

from cfme import test_requirements

pytestmark = [test_requirements.distributed]


@pytest.mark.tier(1)
@pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                         reason="it isn't applicable to pod appliance")
def test_v2_key_permissions(appliance):
    """Verifies that the v2_key has proper permissions

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        initialEstimate: 1/60h
    """
    stdout = appliance.ssh_client.run_command(
        "stat --format '%a' /var/www/miq/vmdb/certs/v2_key").output
    assert int(stdout) == 400
