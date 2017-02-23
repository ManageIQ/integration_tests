import pytest
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import Quadicon
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_credentials_quads(provider):
    navigate_to(InfraProvider, 'All')
    quad = Quadicon(provider.name, qtype='infra_prov')
    checked = str(quad.creds).split('-')[0]
    assert checked == 'checkmark'
