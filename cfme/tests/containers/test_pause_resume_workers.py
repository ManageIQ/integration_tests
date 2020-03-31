import time

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


def check_ems_state_in_diagnostics(appliance, provider):
    workers_view = navigate_to(appliance.collections.diagnostic_workers, 'AllDiagnosticWorkers')
    workers_view.browser.refresh()
    try:
        if workers_view.workers_table.rows(
                name=f'Event Monitor for Provider: {provider.name}').next():
            return True
    except Exception:
        return False


@pytest.mark.ignore_stream("5.11")
def test_pause_and_resume_provider_workers(appliance, provider, request):
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

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    view = navigate_to(provider, "Details")
    # pause the provider
    view.toolbar.configuration.item_select(provider.pause_provider_text, handle_alert=True)
    ems_worker_state = check_ems_state_in_diagnostics(appliance, provider)
    assert not ems_worker_state, "Diagnostics shows that workers are running after pause provider"

    @request.addfinalizer
    def _finalize():
        if not provider.is_provider_enabled:
            view = navigate_to(provider, "Details")
            view.toolbar.configuration.item_select(provider.resume_provider_text, handle_alert=True)

    view = navigate_to(provider, "Details")
    # resume the provider
    view.toolbar.configuration.item_select(provider.resume_provider_text, handle_alert=True)
    ems_worker_state = wait_for(lambda: not check_ems_state_in_diagnostics(appliance, provider))
    assert ems_worker_state, "Diagnostics shows that workers are not running after resume provider"


@pytest.mark.parametrize('from_collections', [True, False], ids=['from_collection', 'from_entity'])
def test_pause_and_resume_single_provider_api(appliance, provider, from_collections,
                                              soft_assert, request):
    """
    Test enabling and disabling a single provider via the CFME API through the ManageIQ API Client
    collection and entity classes.

    RFE: BZ 1507812

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    match_disable = 'Pausing' if appliance.version > 5.11 else 'Disabling'

    evm_tail_disable = LogValidator('/var/www/miq/vmdb/log/evm.log',
                                    matched_patterns=[fr'.*{match_disable} EMS \[{provider.name}\] '
                                                      fr'id \[{provider.id}\].*'])
    evm_tail_disable.start_monitoring()
    if from_collections:
        rep_disable = appliance.collections.containers_providers.pause_providers(provider)
        # collections class returns a list of dicts containing the API response.
        soft_assert(rep_disable[0].get('success'),
                    f'Disabling provider {provider.name} failed')
    else:
        rep_disable = provider.pause()
        # entity class returns a dict containing the API response
        soft_assert(rep_disable.get('success'), f'Disabling provider {provider.name} failed')
    soft_assert(not provider.is_provider_enabled, 'Provider {} is still enabled'
                .format(provider.name))
    assert evm_tail_disable.validate()
    # Verify all monitoring workers have been shut down
    assert wait_for(lambda: not check_ems_state_in_diagnostics(appliance, provider))
    # Pausing is an asynchronous call. It takes a bit for the provider to full pause. There is no
    # log that indicates that the provider is full paused so sleeping 15 seconds for now.
    # Enhancement BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1752642
    # TODO: Remove when BZ has be verified
    time.sleep(15)
    # Create a project on the OpenShift provider via wrapanapi
    project_name = fauxfactory.gen_alpha(8).lower()
    provider.mgmt.create_project(name=project_name)

    @request.addfinalizer
    def _finalize():
        provider.mgmt.delete_project(name=project_name)

    project = appliance.collections.container_projects.instantiate(name=project_name,
                                                                   provider=provider)
    # Trigger an appliance refresh
    provider.refresh_provider_relationships()
    # Objects to appear in the GUI immediately
    soft_assert(
        wait_for(
            lambda: not project.exists,
            delay=5,
            num_sec=100,
            message="waiting for project to display"
        ),
        f'Project {project_name} exists even though provider has been disabled'
    )

    match_enable = 'Resuming' if appliance.version > 5.11 else 'Enabling'

    evm_tail_enable = LogValidator('/var/www/miq/vmdb/log/evm.log',
                                   matched_patterns=[fr'.*{match_enable} EMS \[{provider.name}\] '
                                                     fr'id \[{provider.id}\].*'])
    evm_tail_enable.start_monitoring()
    if from_collections:
        rep_enable = appliance.collections.containers_providers.resume_providers(provider)
        soft_assert(rep_enable[0].get('success'), f'Enabling provider {provider.name} failed')
    else:
        rep_enable = provider.resume()
        soft_assert(rep_enable.get('success'), f'Enabling provider {provider.name} failed')
    soft_assert(provider.is_provider_enabled, f'Provider {provider.name} is still disabled')
    assert evm_tail_enable.validate()
    provider.refresh_provider_relationships()
    soft_assert(
        wait_for(
            lambda: project.exists,
            delay=5,
            num_sec=100,
            message="waiting for project to display"
        ),
        f'Project {project_name} does not exists even though provider has been enabled'
    )

# TODO Add the following test when multi provider marker is implemented

# def test_pause_and_resume_multiple_provider_api(appliance, provider, second_provider, app_creds,
#                                                 soft_assert, request):
