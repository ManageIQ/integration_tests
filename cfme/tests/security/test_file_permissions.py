import pytest
from cfme.utils import version


@pytest.mark.uncollectif(lambda: version.current_version() < '5.6', reason='Only valid for >5.7')
def test_v2_key_permissions(appliance):
    """Verifies that the v2_key has proper permissions"""
    stdout = appliance.ssh_client.run_command(
        "stat --format '%a' /var/www/miq/vmdb/certs/v2_key")[1]
    assert int(stdout) == 400
