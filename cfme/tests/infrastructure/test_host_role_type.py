import pytest
from utils import testgen
from cfme.web_ui import Quadicon, toolbar
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel

def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")
ROLES = ['Compute', 'Controller', 'BlockStorage', 'ObjectStorage',
         'CephStorage']


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_role_type(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    result = False
    for quad in my_quads:
        role_name = str(quad).split(" ")[1].replace(')', '').replace('(', '')
        if role_name in ROLES:
            result = True
    assert result

