"""Common tests for infrastructure provider"""

import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_api_port(provider):
    port = provider.get_yaml_data()['endpoints']['default']['api_port']
    assert provider.summary.properties.api_port.value == port, 'Invalid API Port'


def test_credentials_quads(provider):
    view = navigate_to(provider, 'All')
    prov_item = view.entities.get_entity(by_name=provider.name, surf_pages=True)
    assert prov_item.data.get('creds') and 'checkmark' in prov_item.data['creds']


def test_delete_provider(provider):
    provider.delete(cancel=False)
    provider.wait_for_delete()
    view = navigate_to(provider, 'All')
    assert provider.name not in [item.name for item in view.entities.get_all(surf_pages=True)]
