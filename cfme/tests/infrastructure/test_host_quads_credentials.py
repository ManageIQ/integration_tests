import pytest
from utils import testgen
from cfme.web_ui import Quadicon
from cfme.infrastructure.host import Host
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_quads_credentials(provider, soft_assert):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        result = host.has_valid_credentials
        soft_assert(result, "Invalid host quadicon credentials")