from utils import testgen
import pytest


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate')]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues,
                        ids=idlist, scope="module")


@pytest.mark.usefixtures("setup_provider_modscope")
def test_api_port(provider, soft_assert):
    soft_assert(str(provider.summary.properties.api_port.value).isdigit(),
                "Invalid API Port")
