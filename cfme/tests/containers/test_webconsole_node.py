import pytest

from cfme.containers.provider import ContainersProvider
from utils import testgen, version
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.node import Node
from cfme.fixtures import pytest_selenium as sel
from utils.blockers import BZ

# CMP-10469


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.mark.meta(blockers=[BZ(1406772)])
def test_webconsole_node():
    """ Verify single sign-on to cockpit from master
    """
    navigate_to(Node, 'All')
    tb.select('List View')
    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    nodes_instances = [r for r in list_tbl.rows()]
    nodes_instances[0].row_element.click()
    tb.select('Open a new browser window with Cockpit for this '
              'VM.  This requires that Cockpit is pre-configured on the VM.')
    assert sel.title() == 'Cockpit'
