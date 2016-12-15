import pytest

from utils import testgen
from utils.version import current_version
from cfme.containers.provider import ContainersProvider
from cfme.containers.node import Node
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.project import Project
from cfme.containers.route import Route
from collections import namedtuple
from cfme.containers.container import Container
import time
from cfme.web_ui import StatusBox
from utils.providers import list_providers_by_class
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.overview import ContainersOverview


pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')


DataSet = namedtuple('DataSet', ['object', 'name'])

DATA_SETS = [
    DataSet(Container, 'Containers'),
    DataSet(Node, 'Nodes'),
    DataSet(Project, 'Projects'),
    DataSet(Pod, 'Pods'),
    DataSet(Service, 'Services'),
    DataSet(Route, 'Routes'),
    DataSet(ContainersProvider, 'Providers')
]


def get_api_object_counts(providers):
    out = {
        ContainersProvider: 0,
        Container: 0,
        Node: 0,
        Pod: 0,
        Service: 0,
        Project: 0,
        Route: 0,
    }
    for provider in providers:
        out[ContainersProvider] += 1
        out[Container] = len(provider.mgmt.list_container())
        out[Node] += len(provider.mgmt.list_node())
        out[Pod] += len(provider.mgmt.list_container_group())
        out[Service] += len(provider.mgmt.list_service())
        out[Project] += len(provider.mgmt.list_project())
        out[Route] += len(provider.mgmt.list_route())
    return out


# CMP-9521


def test_containers_overview_data_integrity(provider):
    """Test data integrity of status boxes in containers dashboard.
    Steps:
        * Go to Containers / Overview
        * All cells should contain the correct relevant information
            # of nodes
            # of providers
            # ...
    """
    navigate_to(ContainersOverview, 'All')
    # We should wait ~2 seconds for the StatusBox population
    # (until we find a better solution)
    # Since we collect images from Openshift and from the pods,
    # images are tested separately
    time.sleep(2)
    statusbox_values = {data_set.object: int(StatusBox(data_set.name).value())
                        for data_set in DATA_SETS}
    api_values = get_api_object_counts(
        list_providers_by_class(ContainersProvider))

    list_img_from_registry = provider.mgmt.list_image()
    list_img_from_registry_splitted = [i.id.split(
        '@sha256:')[-1] for i in list_img_from_registry]

    list_img_from_openshift = provider.mgmt.list_image_openshift()
    list_img_from_openshift_splitted = [d['name']
                                        for d in list_img_from_openshift]
    list_img_from_openshift_parsed = [i[7:].split(
        '@sha256:')[-1] for i in list_img_from_openshift_splitted]

    for s in list_img_from_openshift_parsed:
        for item in list_img_from_registry_splitted:
            if item not in list_img_from_openshift_parsed:
                list_img_from_openshift_parsed.append(item)

    assert len(list_img_from_openshift_parsed) == StatusBox('images').value()

    list_all_rgstr = provider.mgmt.list_image_registry()
    list_all_rgstr_revised = [i.host for i in list_all_rgstr]
    list_all_rgstr_new = filter(lambda ch: 'openshift3' not in ch, list_all_rgstr_revised)

    assert len(list_all_rgstr_new) == StatusBox('registries').value()

    results = {}
    for cls in DATA_SETS:
        results[cls.object] = api_values[cls.object] == statusbox_values[cls.object]
    if not all(results.values()):
        pytest.fail('There is a mismatch between API and UI values:\n{}'.format(
            '\n'.join(['{}: {} (API) != {} (UI)'.format(
                obj.__name__, api_values[obj], statusbox_values[obj])
                for obj, is_pass in results.items() if not is_pass])))
