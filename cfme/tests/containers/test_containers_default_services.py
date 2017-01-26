import pytest
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from cfme.containers.service import Service, list_tbl
from cfme.containers.provider import ContainersProvider
from cfme.fixtures import pytest_selenium as sel


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


DefaultServices = ['frontend',
                   'frontend-prod',
                   'jenkins',
                   'kubernetes',
                   'router']


# CMP-9884

def test_containers_default_services():
    """This test ensures that default container services are existing after provider setup

    Steps:
        * Go to Compute -> Container services.

    Expected result:
        ALL DefaultServices above should exist (appear in the table).
    """
    navigate_to(Service, 'All')
    sel.wait_until(lambda *args: not sel.is_displayed_text('No Records Found'),
                   'There is no container services at all. ((!) No Records Found)'
                   'Maybe the provider didn\'t load?', timeout=120.0)
    names = [r[2].text for r in list_tbl.rows()]
    not_in_list = [serv for serv in DefaultServices if serv not in names]
    if not_in_list:
        pytest.fail('The following services not found: {}'.format(not_in_list))
