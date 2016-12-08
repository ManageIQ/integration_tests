import pytest

from utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from utils import testgen
from utils.version import current_version
from cfme.web_ui import toolbar as tb

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

# CMP-9878


def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button.

    """

    navigate_to(ContainersProvider, 'All')
    provider.load_details()
    tb.select('Reload Current Display')
    provider.validate_stats(ui=True)
