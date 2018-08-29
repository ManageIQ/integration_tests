import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


def check_ems_state_in_diagnostics(appliance, provider):
    workers_view = navigate_to(appliance.collections.diagnostic_workers, 'AllDiagnosticWorkers')
    workers_view.browser.refresh()
    try:
        if workers_view.workers_table.rows(
                name='Event Monitor for Provider: {}'.format(provider.name)).next():
            return True
    except Exception:
        return False


def test_pause_and_resume_provider_workers(appliance, provider):
    """
    Basic workers testing for pause and resume for a container provider
    Tests steps:
        1. Navigate to provider page
        2. Pause the provider
        3. navigate to : User -> Configuration -> Diagnostics ->  Workers
        4. Validate the ems_ workers are not found
        5. Navigate to provider page
        6. Resume the provider
        7. navigate to : User -> Configuration -> Diagnostics ->  Workers
        8. Validate the ems_ workers are started
    """
    view = navigate_to(provider, "Details")
    # pause the provider
    view.toolbar.configuration.item_select(provider.pause_provider_text, handle_alert=True)
    ems_worker_state = check_ems_state_in_diagnostics(appliance, provider)
    assert not ems_worker_state, "Diagnostics shows that workers are running after pause provider"

    view = navigate_to(provider, "Details")
    # resume the provider
    view.toolbar.configuration.item_select(provider.resume_provider_text, handle_alert=True)
    ems_worker_state = check_ems_state_in_diagnostics(appliance, provider)
    assert ems_worker_state, "Diagnostics shows that workers are not running after resume provider"
