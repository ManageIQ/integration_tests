import pytest

from cfme.containers.provider import ContainersProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.utils import testgen, version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ


pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: version.current_version() < "5.7"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-10255')
@pytest.mark.meta(blockers=[BZ(1406772, forced_streams=["5.7", "5.8"])])
def test_cockpit_button_access(provider, appliance, soft_assert):
    """ The test verifies the existence of cockpit "Web Console"
        button on master node, then presses on the button and
        opens up the cockpit main page in a new window. Then
        we verify the title of the main cockpit page. The test
        will not work until the single sign-on bug is fixed

    """

    collection = appliance.collections.nodes
    nodes = collection.all()
    node = [node for node in nodes if 'master' in node.name][0]
    navigate_to(node, 'Details')

    soft_assert(
        tb.exists(
            'Open a new browser window with Cockpit for this '
            'VM.  This requires that Cockpit is pre-configured on the VM.'),
        'No "Web Console" button found')
    tb.select('Open a new browser window with Cockpit for this '
              'VM.  This requires that Cockpit is pre-configured on the VM.')

    port_num = ':9090/system'
    url_cockpit = provider.hostname + port_num
    sel.get(url_cockpit)
    title_pg = sel.title()
    soft_assert(title_pg == 'Cockpit', 'Cockpit main page failed to open')
