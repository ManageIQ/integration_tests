from collections import namedtuple

import pytest

from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node
from cfme.containers.overview import ContainersOverview
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from cfme.containers.route import Route
from cfme.containers.service import Service
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


DataSet = namedtuple('DataSet', ['object', 'name'])

tested_objects = (
    ImageRegistry, Container, Project, Pod, Service, Route, ContainersProvider, Node
)


def get_api_object_counts(appliance):
    out = {
        ContainersProvider: 0,
        Container: 0,
        ImageRegistry: 0,
        Node: 0,
        Pod: 0,
        Service: 0,
        Project: 0,
        Route: 0
    }
    for provider in appliance.managed_known_providers:
        if isinstance(provider, ContainersProvider):
            out[ContainersProvider] += 1
            out[Node] += len(provider.mgmt.list_node())
            out[Pod] += len(provider.mgmt.list_pods())
            out[Service] += len(provider.mgmt.list_service())
            out[Project] += len(provider.mgmt.list_project())
            out[Route] += len(provider.mgmt.list_route())
            # TODO image count? list_templates too high, list_image_stream_images too low
            out[ImageRegistry] += len(provider.mgmt.list_image_registry())
            listed_containers = provider.mgmt.list_container()
            # Get all container pods
            out[Container] += sum(1 for pod in listed_containers for c in pod)

    return out


def test_containers_overview_data_integrity(appliance, soft_assert):
    """Test data integrity of status boxes in containers dashboard.
    Steps:
        * Go to Containers / Overview
        * All cells should contain the correct relevant information
            # of nodes
            # of providers
            # ...

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    view = navigate_to(ContainersOverview, 'All')
    api_values = get_api_object_counts(appliance)

    for cls in tested_objects:
        statusbox_value = view.status_cards(cls.PLURAL.split(' ')[-1]).value
        soft_assert(
            api_values[cls] == statusbox_value,
            'There is a mismatch between API and UI values: {}: {} (API) != {} (UI)'.format(
                cls.__name__, api_values[cls], statusbox_value
            )
        )
