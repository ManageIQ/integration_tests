import pytest
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


def get_pause_resume_buttons(view):
    # ensure resume option is exist
    resume_option = filter(lambda item: "resume" in item.lower(), view.toolbar.configuration.items)
    assert resume_option, "Not resume provider option is available in the configuration menu"
    resume_option = resume_option.pop()

    # ensure pause option is exsit
    pause_option = filter(lambda item: "pause" in item.lower(), view.toolbar.configuration.items)
    assert pause_option, "Not pause provider option is available in the configuration menu"
    pause_option = pause_option.pop()

    return pause_option, resume_option


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


def check_ems_state_in_diagnostics(appliance, provider):
    workers_view = navigate_to(appliance.collections.diagnostic_workers, 'AllDiagnosticWorkers')

    workers_view.browser.refresh()

    ems_worker_is_running = False

    for row in workers_view.workers_table.rows():

        name = getattr(row, "Name")

        uri_queue_name = getattr(row, "URI / Queue Name")

        assert name, "'Name' column not found in workers table"

        assert uri_queue_name, "'URI / Queue Name' column not found in workers table"

        if "Event Monitor for Provider" in name.text\
                and provider.name in name.text \
                and "ems_" in uri_queue_name.text:
            ems_worker_is_running = True

    return ems_worker_is_running
