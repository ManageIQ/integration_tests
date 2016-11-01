import pytest
import time

from cfme.containers.container import Container, list_tbl as list_tbl_containers
from cfme.containers.pod import Pod, list_tbl as list_tbl_pods
from cfme.containers.project import Project, list_tbl as list_tbl_projects
from cfme.containers.route import Route, list_tbl as list_tbl_routes
from cfme.containers.service import Service, list_tbl as list_tbl_services
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox, Quadicon
from utils import testgen
from utils.version import current_version
from cfme.containers.provider import ContainersProvider

pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# TEST_DATAS: Referenced from: Menu.sections()
# TODO: Refactor to container objects with valid navmazing destinations
TEST_DATAS = [
    # (Node, 'containers_nodes', 'Nodes', list_tbl_nodes),
    (Container, 'containers_containers', 'Containers', list_tbl_containers),
    # (ImageRegistry, 'containers_image_registries', 'Registries', list_tbl_image_registrys),
    (Project, 'containers_projects', 'Projects', list_tbl_projects),
    (Pod, 'containers_pods', 'Pods', list_tbl_pods),
    (Service, 'containers_services', 'Services', list_tbl_services),
    # (Image, 'containers_images', 'Images', list_tbl_images),
    (Route, 'containers_routes', 'Routes', list_tbl_routes),
    (ContainersProvider, 'containers_providers', 'Providers')
]
#   CMP-9521


@pytest.mark.parametrize(('test_data'), TEST_DATAS)
def test_data_integrity_for_topology(test_data):
    """ This test verifies that every status box value under Containers Overview is identical to the
    number present on its page.
    Steps:
        * Go to Containers / Overview
        * All cells should contain the correct relevant information
            # of nodes
            # of providers
            # ...
    """
    section_values = {}
    sel.force_navigate('container_dashboard')
    # We should wait ~2 seconds for the StatusBox population
    # (until we find a better solution)
    time.sleep(2)
    status_box = StatusBox(test_data[2])
    section_values[test_data[0]] = int(status_box.value())
    sel.force_navigate(test_data[1])
    if section_values[test_data[0]] > 0:
        if test_data[0] is ContainersProvider:
            assert len(map(lambda i: i, Quadicon.all())) == section_values[test_data[0]]
        else:
            assert len(map(lambda r: r, test_data[3].rows())
                       ) == section_values[test_data[0]]
    else:
        assert sel.is_displayed_text('No Records Found.')
