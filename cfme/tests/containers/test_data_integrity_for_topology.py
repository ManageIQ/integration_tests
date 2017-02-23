import pytest
import time
from collections import namedtuple

from selenium.common.exceptions import NoSuchElementException

from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import NodeCollection
from cfme.containers.overview import ContainersOverview
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from cfme.containers.route import Route
from cfme.containers.service import Service
from cfme.containers.image import Image
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox, Quadicon, toolbar as tb, search
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

DataSet = namedtuple('DataSet', ['object', 'name'])

DATA_SETS = [
    DataSet(Container, 'Containers'),
    DataSet(NodeCollection, 'Nodes'),
    DataSet(Project, 'Projects'),
    DataSet(Pod, 'Pods'),
    DataSet(Service, 'Services'),
    DataSet(Image, 'Images'),
    DataSet(Route, 'Routes'),
    DataSet(ContainersProvider, 'Providers'),
    DataSet(ImageRegistry, 'Registries')
]
# CMP-9820 CMP-9821 CMP-9822 CMP-9823 CMP-9824 CMP-9825 CMP-9826 CMP-9827


@pytest.mark.parametrize(('test_data'), DATA_SETS)
def test_data_integrity_for_topology(test_data):
    """ This test verifies that every status box value under Containers Overview is identical to the
    number present on its page.
    """
    navigate_to(ContainersOverview, 'All')
    # We should wait ~2 seconds for the StatusBox population
    # (until we find a better solution)
    time.sleep(2)
    status_box = StatusBox(test_data.name)
    statusbox_value = int(status_box.value())
    navigate_to(test_data.object, 'All')
    if statusbox_value > 0:
        tb.select('Grid View')
        try:
            search.ensure_no_filter_applied()
        except NoSuchElementException:
            pass
        assert len(list(Quadicon.all())) == statusbox_value
    else:
        assert sel.is_displayed_text('No Records Found.')
