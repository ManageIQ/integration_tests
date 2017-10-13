import pytest

from cfme import test_requirements

pytestmark = [test_requirements.distributed]


@pytest.mark.tier(1)
def test_v2_key_permissions(appliance):
    """Verifies that the v2_key has proper permissions"""
    stdout = appliance.ssh_client.run_command(
        "stat --format '%a' /var/www/miq/vmdb/certs/v2_key").output
    assert int(stdout) == 400
