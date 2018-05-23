import pytest

from cfme.containers.provider import ContainersProvider
from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.service import Service
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.ignore_stream('5.8'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]

PROJECT_NAME = 'test-project-dashboard'  # Predefine project for this test


@pytest.fixture(scope='function')
def container_project_instance(appliance, provider):
    collection_object = appliance.collections.container_projects
    return collection_object.instantiate(name=PROJECT_NAME, provider=provider)


def get_api_object_counts(appliance, project_name, provider):
    """ Fetches amount of Containers/Services/Images from the API per selected project name"""
    assert isinstance(provider, ContainersProvider)
    return {
        Container: len(provider.mgmt.list_container(project_name=project_name)),
        Service: len(provider.mgmt.list_service(project_name=project_name)),
        Image: len(get_container_images_amt(provider, project_name))
    }


def get_container_images_amt(provider, project_name=None):
    """ Fetches images amount from the API per selected project name"""
    project_images = [
        img for img
        in provider.mgmt.list_image()
        if img.image_project_name == project_name
    ]
    return project_images


def get_api_pods_names(provider):
    """ Fetches Pod names from the API per selected project name"""
    pod_name = []
    for pod in provider.mgmt.list_container_group(project_name=PROJECT_NAME):
        pod_name.append(pod.name)
    return pod_name


@pytest.mark.polarion('CMP-10806')
def test_projects_dashboard_pods(provider, soft_assert, container_project_instance):
    """Tests data integrity of Pods names in Pods status box in Projects Dashboard.
    Steps:
        * Go to Projects / Dashboard View
        * Compare the data in the Pods status box to API data for
        Pods names

    Polarion:
        assignee: None
        initialEstimate: None
    """
    api_pod_names = get_api_pods_names(provider)
    view = navigate_to(container_project_instance, 'Dashboard')
    for field in view.pods.fields:
        soft_assert(
            field in api_pod_names,
            'There is a mismatch between API and UI values: {} (API) != {} (UI)'.format(
                api_pod_names, field
            )
        )


@pytest.mark.polarion('CMP-10805')
def test_projects_dashboard_icons(provider, appliance, soft_assert, container_project_instance):
    """Tests data integrity of Containers/Images/Services number in
    Projects Dashboard's status boxes.
    Steps:
        * Go to Projects / Dashboard View
        * Compare the data in the status boxes to API data forz
        Containers/Images/Services numbers

    Polarion:
        assignee: None
        initialEstimate: None
    """
    api_values = get_api_object_counts(appliance, PROJECT_NAME, provider)
    view = navigate_to(container_project_instance, 'Dashboard')
    # Getting the value (number of classes), from each status icon on project dashboard view,
    # Container, Images and Services.
    for containers_cls in api_values.keys():
        # Getting the value of status icon box by split the 'images'
        # Out of PLURAL 'Container Images' for example.
        statusbox_value = getattr(view, containers_cls.PLURAL.split(' ')[-1].lower()).value
        soft_assert(
            api_values[containers_cls] == statusbox_value,
            'There is a mismatch between API and UI values: {}: {} (API) != {} (UI)'.format(
                containers_cls.__name__, api_values[containers_cls], statusbox_value
            )
        )
