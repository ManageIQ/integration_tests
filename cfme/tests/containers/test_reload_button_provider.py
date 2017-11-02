import pytest

from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.provider([ContainersProvider], scope='function')
]


@pytest.mark.polarion('CMP-9878')
def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button.
    """

    provider.validate_stats(ui=True)
