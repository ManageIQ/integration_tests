import pytest
from collections import namedtuple

from cfme.containers.provider import ContainersProvider
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.containers.overview import ContainersOverview

from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


DataSet = namedtuple('DataSet', ['object', 'name'])


# TODO: Add Image, Container, ImageRegistry
# TODO Add Node back into the list when other classes are updated to use WT views and widgets.
tested_objects = (Project, Pod, Service, Route, ContainersProvider)


def get_api_object_counts(appliance):
    out = {
        ContainersProvider: 0,
        # TODO Add back in with Node.
        # Node: 0,
        Pod: 0,
        Service: 0,
        Project: 0,
        Route: 0
    }
    for provider in appliance.managed_known_providers:
        if isinstance(provider, ContainersProvider):
            out[ContainersProvider] += 1
            # TODO Add back in with Node
            # out[Node] += len(provider.mgmt.list_node())
            out[Pod] += len(provider.mgmt.list_container_group())
            out[Service] += len(provider.mgmt.list_service())
            out[Project] += len(provider.mgmt.list_project())
            out[Route] += len(provider.mgmt.list_route())
    return out


@pytest.mark.polarion('CMP-9521')
def test_containers_overview_data_integrity(appliance, soft_assert):
    """Test data integrity of status boxes in containers dashboard.
    Steps:
        * Go to Containers / Overview
        * All cells should contain the correct relevant information
            # of nodes
            # of providers
            # ...
    """
    view = navigate_to(ContainersOverview, 'All')
    api_values = get_api_object_counts(appliance)

    for cls in tested_objects:
        statusbox_value = getattr(view, cls.PLURAL.split(' ')[-1].lower()).value
        soft_assert(
            api_values[cls] == statusbox_value,
            'There is a mismatch between API and UI values: {}: {} (API) != {} (UI)'.format(
                cls.__name__, api_values[cls], statusbox_value
            )
        )
