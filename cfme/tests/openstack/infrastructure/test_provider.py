"""Common tests for infrastructure provider"""

import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module'),
]


def test_api_port(provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    view_details = navigate_to(provider, 'Details')
    port = provider.data['endpoints']['default']['api_port']
    api_port = int(view_details.entities.summary('Properties').get_text_of('API Port'))
    assert api_port == port, 'Invalid API Port'

def test_credentials_quads(provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    view = navigate_to(provider, 'All')
    prov_item = view.entities.get_entity(name=provider.name, surf_pages=True)
    assert prov_item.data.get('creds') and 'checkmark' in prov_item.data['creds']


def test_delete_provider(provider):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    provider.delete(cancel=False)
    provider.wait_for_delete()
    view = navigate_to(provider, 'All')
    assert provider.name not in [item.name for item in view.entities.get_all(surf_pages=True)]
