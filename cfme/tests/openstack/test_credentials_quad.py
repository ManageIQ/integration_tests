import pytest
from utils import testgen
from cfme.web_ui import Quadicon
from cfme.fixtures import pytest_selenium as sel


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_credentials_quads(provider):
    provider.load_details()
    sel.force_navigate("infrastructure_providers")
    quad = Quadicon(provider.name, qtype='infra_prov')
    checked = str(quad.creds).split('-')[0]
    assert checked == 'checkmark'
