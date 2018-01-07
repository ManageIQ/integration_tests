"""Common tests for infrastructure provider"""

import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module'),
]


def test_api_port(provider):
<<<<<<< HEAD
    view_details = navigate_to(provider, "Details")
    port = provider.get_yaml_data()['endpoints']['default']['api_port']
    assert int(view_details.entities.properties.get_text_of('API Port')) == port, 'Invalid API Port'
=======
    port = provider.data['endpoints']['default']['api_port']
    assert provider.summary.properties.api_port.value == port, 'Invalid API Port'
>>>>>>> ae8a0c5d1ba1624abc4b9568432435241e7872e3


def test_credentials_quads(provider):
    view = navigate_to(provider, 'All')
    prov_item = view.entities.get_entity(name=provider.name, surf_pages=True)
    assert prov_item.data.get('creds') and 'checkmark' in prov_item.data['creds']


def test_delete_provider(provider):
    provider.delete(cancel=False)
    provider.wait_for_delete()
    view = navigate_to(provider, 'All')
    assert provider.name not in [item.name for item in view.entities.get_all(surf_pages=True)]
