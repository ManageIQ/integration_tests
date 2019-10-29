import pytest

from cfme import test_requirements
from cfme.utils.auth import get_auth_crud

pytestmark = [test_requirements.auth]

# External auth specific test cases (e.g. freeipa)


@pytest.fixture
def freeipa_provider():
    auth_prov = get_auth_crud("freeipa03")
    # turn off ntp
    auth_prov.ssh_client.run_command("systemctl stop ntpd")
    yield auth_prov
