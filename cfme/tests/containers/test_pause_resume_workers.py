from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to
import pytest


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


def get_pause_resume_buttons(view):
    resume_option = [menu_item for menu_item in view.toolbar.configuration.items if
                     "resume this containers provider" in menu_item.lower()]
    # ensure resume option is exists
    assert resume_option, "No resume provider option is available in the configuration menu"
    resume_option = resume_option.pop()

    pause_option = [menu_item for menu_item in view.toolbar.configuration.items if
                    "pause this containers provider" in menu_item.lower()]
    # ensure pause option is exists
    assert pause_option, "No pause provider option is available in the configuration menu"
    pause_option = pause_option.pop()

    return pause_option, resume_option


def check_ems_state_in_diagnostics(appliance, provider):
    workers_view = navigate_to(appliance.collections.diagnostic_workers, 'AllDiagnosticWorkers')
    workers_view.browser.refresh()
    try:
        rows = workers_view.workers_table.rows(
            name='Event Monitor for Provider: {}'.format(provider.name))
        for r in rows:
            return True
        else:
            return False
    except Exception:
        return False
    return False


@pytest.mark.polarion('10790', '10791')
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
    pause_option, resume_option = get_pause_resume_buttons(view)
    # pause the provider
    view.toolbar.configuration.item_select(pause_option, handle_alert=True)
    ems_worker_state = check_ems_state_in_diagnostics(appliance, provider)
    assert not ems_worker_state, "Diagnostics shows that workers are running after pause provider"

    view = navigate_to(provider, "Details")
    # resume the provider
    view.toolbar.configuration.item_select(resume_option, handle_alert=True)
    ems_worker_state = check_ems_state_in_diagnostics(appliance, provider)
    assert ems_worker_state, "Diagnostics shows that workers are not running after resume provider"
