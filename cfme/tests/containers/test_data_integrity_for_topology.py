import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox, Table
from utils import testgen
import time
from cfme.containers.node import Node
from cfme.containers.pod import Pod
from cfme.containers.container import Container
from cfme.containers.project import Project
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.service import Service
from cfme.containers.image import Image
from cfme.containers.route import Route
from utils.version import current_version
from cfme.containers.provider import Provider

pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: current_version() < "5.6" and provider.version > 3.2),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CONTAINER_CLASSES: Referenced from: Menu.sections()
CONTAINER_CLASSES = {
    Node: (
        'containers_nodes', 'Nodes'), Container: (
            'containers_containers', 'Containers'), ImageRegistry: (
                'containers_image_registries', 'Registries'), Project: (
                    'containers_projects', 'Projects'), Pod: (
                        'containers_pods', 'Pods'), Service: (
                            'containers_services', 'Services'), Image: (
                                'containers_images', 'Images'), Route: (
                                    'containers_routes', 'Routes'), Provider: (
                                        'containers_providers', 'Providers')}
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
    # We should wait a second to let it be loaded (until we find a better
    # solution)
    time.sleep(2)
    for cls, properties in CONTAINER_CLASSES.items():
        status_box = StatusBox(properties[1])
        section_values[cls] = int(status_box.value())
    for cls, properties in CONTAINER_CLASSES.items():
        sel.force_navigate(properties[0])
        if section_values[cls] > 0:
            if cls == Provider:
                icons = sel.elements('//div[@id="quadicon"]')
                assert len(icons) == section_values[cls]
            else:
                table = Table(table_locator='//div[@id="list_grid"]//table')
                assert len(map(lambda r: r, table.rows())
                           ) == section_values[cls]
        else:
            assert sel.is_displayed_text('No Records Found.')
