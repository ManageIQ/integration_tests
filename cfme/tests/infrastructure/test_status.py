from utils import testgen
import pytest

pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")

@pytest.mark.usefixtures("setup_provider_modscope")
def test_status(provider, soft_assert):
    soft_assert(
        provider.summary.status.default_credentials.value != "Valid",
        "Default credentials are invalid <<<<<< test BLOCK >>>>>>>>>>>>")
    soft_assert(
         provider.summary.status.amqp_credentials.value != "Valid",
        "Events credentials are invalid")
