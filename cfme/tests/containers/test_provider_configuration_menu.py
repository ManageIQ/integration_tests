import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.utils import testgen
from cfme.utils.version import current_version
from cfme.web_ui import toolbar as tb, Quadicon, breadcrumbs_names
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


def select_first_provider_and_get_its_name():
    navigate_to(ContainersProvider, 'All')
    tb.select('Grid View')
    Quadicon.select_first_quad()
    return Quadicon.get_first_quad_title()


@pytest.mark.polarion('CMP-9880')
def test_edit_selected_containers_provider():
    '''Testing Configuration -> Edit... button functionality
    Step:
        In Providers summary page - click configuration
        menu and select "Edit this containers provider"
    Expected result:
        The user should be navigated to the container's basic information page.'''
    name = select_first_provider_and_get_its_name()
    provider = ContainersProvider(name)
    provider.load_details()
    navigate_to(provider, 'EditFromDetails')
    assert 'Edit Containers Providers \'{}\''.format(name) == breadcrumbs_names()[-1]


@pytest.mark.polarion('CMP-9881')
def test_remove_selected_containers_provider():
    '''Testing Configuration -> Remove... button functionality
    Step:
        In Providers summary page - click configuration menu and select
        "Remove this container provider from VMDB"
    Expected result:
        The user should be shown a warning message following a
        success message that the provider has been deleted from VMDB.'''
    name = select_first_provider_and_get_its_name()
    ContainersProvider(name).delete(cancel=False)
    assert wait_for(lambda: not Quadicon(name).exists,
                    msg='Waiting for containers provider to be removed.',
                    fail_func=sel.refresh,
                    delay=5,
                    num_sec=60.0), 'Failed to remove containers provider'
