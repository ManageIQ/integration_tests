
import pytest
from utils import testgen
from cfme.web_ui import Quadicon
from cfme.fixtures import pytest_selenium as sel


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues,
                        ids=idlist, scope="module")


@pytest.mark.usefixtures("setup_provider_modscope")
def test_credentials_quads(provider):
    provider.load_details()
    sel.force_navigate("infrastructure_providers")
    quad = Quadicon(provider.name, qtype='infra_prov')
    checked = str(quad.creds)
    assert checked == 'checkmark'
