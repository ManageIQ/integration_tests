import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils import testgen, version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-9878')
def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button.
    """

    provider.validate_stats(ui=True)
