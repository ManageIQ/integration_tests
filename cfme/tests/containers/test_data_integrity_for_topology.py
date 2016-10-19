import pytest
import time

from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.containers.service import Service
from cfme.containers.image import Image
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox, Quadicon
from utils import testgen
from utils.version import current_version
from cfme.containers.provider import ContainersProvider
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.node import Node
from collections import namedtuple
from cfme.web_ui import toolbar as tb

pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

DataSet = namedtuple('DataSet', ['object', 'name'])

# TODO: add the following to the list once possible:
DATA_SETS = [
    DataSet(Container, 'Containers'),
    DataSet(Node, 'Nodes'),
    DataSet(Project, 'Projects'),
    DataSet(Pod, 'Pods'),
    DataSet(Service, 'Services'),
    DataSet(Image, 'Images'),
    DataSet(Route, 'Routes'),
    DataSet(ContainersProvider, 'Providers'),
    DataSet(ImageRegistry, 'Registries')
]
#   CMP-9521


@pytest.mark.parametrize(('test_data'), DATA_SETS)
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
    sel.force_navigate('container_dashboard')
    # We should wait ~2 seconds for the StatusBox population
    # (until we find a better solution)
    time.sleep(2)
    status_box = StatusBox(test_data.name)
    statusbox_value = int(status_box.value())
    navigate_to(test_data.object, 'All')
    if statusbox_value > 0:
        tb.select('Grid View')
        assert len(map(lambda i: i, Quadicon.all())) == statusbox_value
    else:
        assert sel.is_displayed_text('No Records Found.')
