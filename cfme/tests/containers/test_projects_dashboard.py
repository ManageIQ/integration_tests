import pytest

from cfme import test_requirements
from cfme.containers.container import Container
from cfme.containers.image import Image
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.ignore_stream('5.8'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
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
        Container: len(flatten_list(provider.mgmt.list_container(namespace=project_name),
                                    flattened_list=[])),
        Service: len(provider.mgmt.list_service(namespace=project_name)),
        # TODO: remove sorted set when wrapanapi updates will return unique image IDs
        # number of unique images
        Image: len(sorted(set(provider.mgmt.list_image_id(namespace=project_name))))
    }


def flatten_list(org_list, flattened_list=None):
    """Expands nested list elements to new flatten list
    Use for get len for of nested list

    Args:
            org_list: (list) nested list
            flattened_list: (list) empty list
    Returns: flatten list
    """
    if not flattened_list:
        flattened_list = []

    for elem in org_list:
        if not isinstance(elem, list):
            flattened_list.append(elem)
        else:
            flatten_list(elem, flattened_list)
    return flattened_list


def get_container_images_amt(provider, project_name=None):
    """ Fetches images amount from the API per selected project name"""
    project_images = [
        img for img
        in provider.mgmt.list_templates()
        if img.project == project_name
    ]
    return project_images


def get_api_pods_names(provider):
    """ Fetches Pod names from the API per selected project name"""
    pod_name = []
    for pod in provider.mgmt.list_pods(namespace=PROJECT_NAME):
        pod_name.append(pod.metadata.name)
    return pod_name


def test_projects_dashboard_pods(provider, soft_assert, container_project_instance):
    """Tests data integrity of Pods names in Pods status box in Projects Dashboard.
    Steps:
        * Go to Projects / Dashboard View
        * Compare the data in the Pods status box to API data for
        Pods names

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
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


def test_projects_dashboard_icons(provider, appliance, soft_assert, container_project_instance):
    """Tests data integrity of Containers/Images/Services number in
    Projects Dashboard's status boxes.
    Steps:
        * Go to Projects / Dashboard View
        * Compare the data in the status boxes to API data forz
        Containers/Images/Services numbers

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
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


def test_project_has_provider(appliance, soft_assert, provider):
    """
    Test provider name existence in all projects table.
    Steps:
      * navigate to all project page
      * get through all the project to ensure that the provider column isn't
        empty on each on each of the projects

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    projects_collection = appliance.collections.container_projects

    all_project_view = navigate_to(projects_collection, "All")
    all_tables_rows = all_project_view.entities.get_all()

    assert all_tables_rows, "No table row was found"

    for row in all_tables_rows:
        curr_project_name = row.data["name"]
        curr_project_provider = row.data["provider"]

        soft_assert(curr_project_provider,
                    f"No Provider found for project {curr_project_name}")
