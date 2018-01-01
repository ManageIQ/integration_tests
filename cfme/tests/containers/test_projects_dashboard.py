import pytest

from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.service import Service
from cfme.containers.project import Project, ProjectCollection

from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]

tested_objects = [Container, Image, Service]
project_name = 'default'  # Selected because it's in every Openshift installation

TEST_ITEMS = [pytest.mark.polarion('CMP-10806')(
    ContainersTestItem(
        Project,
        'CMP-10806',
        collection_object=ProjectCollection
    )
)]


def get_api_object_counts(appliance, project_name):
    """ Fetches amount of Containers/Services/Images from the API per selected project name"""
    out = {
        Container: 0,
        Service: 0,
        Image: 0
    }
    for provider in appliance.managed_known_providers:
        if isinstance(provider, ContainersProvider):
            out[Container] += len(provider.mgmt.list_container_group(project_name))
            out[Service] += len(provider.mgmt.list_service(project_name))
            out[Image] += len(get_container_images_amt(provider, project_name))
    return out


def get_container_images_amt(provider, project_name=None):
    """ Fetches images amount from the API per selected project name"""
    images = provider.mgmt.list_image()
    project_images = []
    for image in images:
        if image.image_project_name == project_name:
            project_images.append(image)
    return project_images


def get_api_pods_names(provider):
    """ Fetches Pod names from the API per selected project name"""
    pod_name = []
    for pod in provider.mgmt.list_container_group(project_name):
        pod_name.append(pod.name)
    return pod_name


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_projects_dashboard_pods(provider, appliance, soft_assert, test_item):
    """Tests data integrity of Pods names in Pods status box in Projects Dashboard.
    Steps:
        * Go to Projects / Dashboard View
        * Compare the data in the Pods status box to API data for
        Pods names
    """
    api_pod_names = get_api_pods_names(provider)
    inst = test_item.collection_object(appliance).get_specific_instance('default')
    view = navigate_to(inst, 'Dashboard')
    for field in view.pods.fields:
        soft_assert(
            field in api_pod_names,
            'There is a mismatch between API and UI values: {} (API) != {} (UI)'.format(
                api_pod_names, field
            )
        )


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_projects_dashboard_icons(appliance, soft_assert, test_item):
    """Tests data integrity of Containers/Images/Services number in
    Projects Dashboard's status boxes.
    Steps:
        * Go to Projects / Dashboard View
        * Compare the data in the status boxes to API data forz
        Containers/Images/Services numbers
    """
    api_values = get_api_object_counts(appliance, project_name)
    inst = test_item.collection_object(appliance).get_specific_instance('default')
    view = navigate_to(inst, 'Dashboard')
    for object in tested_objects:
        statusbox_value = getattr(view, object.PLURAL.split(' ')[-1].lower()).value
        soft_assert(
            api_values[object] == statusbox_value,
            'There is a mismatch between API and UI values: {}: {} (API) != {} (UI)'.format(
                object.__name__, api_values[object], statusbox_value
            )
        )
