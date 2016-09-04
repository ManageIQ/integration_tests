import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox, Quadicon
from utils import testgen
import time
from cfme.containers.node import Node, list_tbl as list_tbl_nodes
from cfme.containers.pod import Pod, list_tbl as list_tbl_pods
from cfme.containers.container import Container, list_tbl as list_tbl_containers
from cfme.containers.project import Project, list_tbl as list_tbl_projects
from cfme.containers.image_registry import ImageRegistry, list_tbl as list_tbl_image_registrys
from cfme.containers.service import Service, list_tbl as list_tbl_services
from cfme.containers.image import Image, list_tbl as list_tbl_images
from cfme.containers.route import Route, list_tbl as list_tbl_routes
from utils.version import current_version
from cfme.containers.provider import Provider

pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CONTAINER_CLASSES: Referenced from: Menu.sections()
CONTAINER_CLASSES = {
    Node: ('containers_nodes', 'Nodes', list_tbl_nodes),
    Container: ('containers_containers', 'Containers', list_tbl_containers),
    ImageRegistry: ('containers_image_registries', 'Registries', list_tbl_image_registrys),
    Project: ('containers_projects', 'Projects', list_tbl_projects),
    Pod: ('containers_pods', 'Pods', list_tbl_pods),
    Service: ('containers_services', 'Services', list_tbl_services),
    Image: ('containers_images', 'Images', list_tbl_images),
    Route: ('containers_routes', 'Routes', list_tbl_routes),
    Provider: ('containers_providers', 'Providers')
}
#   CMP-9521


def test_data_integrity_for_topology():
    '''
    This test verify that every Status box value under Containers Overview
    is identical to the number presents on its page.
    Step:
        In CFME go to Containers -> Overview
    Expected result:
        All cells should contain the correct relevant information
            # of Providers
            # of Nodes
            ...
    '''
    section_values = {}
    sel.force_navigate('container_dashboard')
    # We should wait ~2 seconds for the StatusBox population
    # (until we find a better solution)
    time.sleep(2)
    for cls, properties in CONTAINER_CLASSES.items():
        status_box = StatusBox(properties[1])
        section_values[cls] = int(status_box.value())
    for cls, properties in CONTAINER_CLASSES.items():
        sel.force_navigate(properties[0])
        if section_values[cls] > 0:
            if cls is Provider:
                assert len(map(lambda i: i, Quadicon.all())) == section_values[cls]
            else:
                assert len(map(lambda r: r, properties[2].rows())
                           ) == section_values[cls]
        else:
            assert sel.is_displayed_text('No Records Found.')
