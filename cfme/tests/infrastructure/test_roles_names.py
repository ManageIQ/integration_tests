
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Quadicon

def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")

ROLES = ['Compute', 'Controller', 'BlockStorage', 'ObjectStorage',
         'CephStorage']



@pytest.mark.usefixtures("setup_provider_modscope")
def test_roles_name(provider):
    sel.force_navigate("infrastructure_clusters")
    my_roles_quads = list(Quadicon.all())
    result = False
    for quad in my_roles_quads:
        role_name = str(quad.name).split('-')[1]
        if role_name in ROLES:
            result = True
    assert result



