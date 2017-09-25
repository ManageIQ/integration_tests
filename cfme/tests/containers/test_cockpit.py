import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


@pytest.mark.polarion('CMP-10255')
@pytest.mark.meta(blockers=[BZ(1406772, forced_streams=["5.7", "5.8"])])
def test_cockpit_button_access(provider, appliance, soft_assert):
    """ The test verifies the existence of cockpit "Web Console"
        button on master node, then presses on the button and
        opens up the cockpit main page in a new window. Then
        we verify the title of the main cockpit page. The test
        will not work until the single sign-on bug is fixed.
    """

    collection = appliance.collections.nodes
    nodes = collection.all()
    node = [node for node in nodes if 'master' in node.name][0]
    view = navigate_to(node, 'Details')

    assert view.toolbar.web_console.is_displayed, 'No "Web Console" button found'
    assert view.toolbar.web_console.active
    view.toolbar.web_console.click()

    port_num = ':9090/system'
    url_cockpit = provider.hostname + port_num
    view.browser.url = url_cockpit
    title_pg = view.browser.selenium.title()
    assert title_pg == 'Cockpit', 'Cockpit main page failed to open'
