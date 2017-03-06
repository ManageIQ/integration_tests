import pytest

from cfme.containers.node import NodeCollection, Node
from utils import testgen, version
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-10255')
def test_cockpit_button_access(provider):
    """ The test verifies the existence of cockpit "Web Console"
        button on each node

    """
    navigate_to(NodeCollection, 'All')
    tb.select('List View')

    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    names = [r.name.text for r in list_tbl.rows()]

    for name in names:
        obj = Node(name, provider)
        obj.load_details()
        assert tb.exists(
            'Open a new browser window with Cockpit for this '
            'VM.  This requires that Cockpit is pre-configured on the VM.')
