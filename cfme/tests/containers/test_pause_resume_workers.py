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

    view = navigate_to(provider, "Details")
    # resume the provider
    view.toolbar.configuration.item_select(provider.resume_provider_text, handle_alert=True)
    ems_worker_state = check_ems_state_in_diagnostics(appliance, provider)
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

    evm_tail_disable = LogValidator('/var/www/miq/vmdb/log/evm.log',
                                    matched_patterns=[r'.*Disabling EMS \[{}\] id \[{}\].*'
                                                      .format(provider.name, str(provider.id))])
    evm_tail_disable.start_monitoring()
    if from_collections:
        rep_disable = appliance.collections.containers_providers.pause_providers(provider)
        # collections class returns a list of dicts containing the API response.
        soft_assert(rep_disable[0].get('success'),
                    'Disabling provider {} failed'.format(provider.name))
    else:
        rep_disable = provider.pause()
        # entity class returns a dict containing the API response
        soft_assert(rep_disable.get('success'), 'Disabling provider {} failed'
                    .format(provider.name))
    soft_assert(not provider.is_provider_enabled, 'Provider {} is still enabled'
                .format(provider.name))
    assert evm_tail_disable.validate()
    # Verify all monitoring workers have been shut down
    assert wait_for(lambda: not check_ems_state_in_diagnostics(appliance, provider))
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
        'Project {p} exists even though provider has been disabled'.format(p=project_name)
    )
    evm_tail_enable = LogValidator('/var/www/miq/vmdb/log/evm.log',
                                   matched_patterns=[r'.*Enabling EMS \[{}\] id \[{}\].*'
                                                     .format(provider.name, str(provider.id))])
    evm_tail_enable.start_monitoring()
    if from_collections:
        rep_enable = appliance.collections.containers_providers.resume_providers(provider)
        soft_assert(rep_enable[0].get('success'), 'Enabling provider {} failed'
                    .format(provider.name))
    else:
        rep_enable = provider.resume()
        soft_assert(rep_enable.get('success'), 'Enabling provider {} failed'.format(provider.name))
    soft_assert(provider.is_provider_enabled, 'Provider {} is still disabled'.format(provider.name))
    assert evm_tail_enable.validate()
    provider.refresh_provider_relationships()
    soft_assert(
        wait_for(
            lambda: project.exists,
            delay=5,
            num_sec=100,
            message="waiting for project to display"
        ),
        'Project {p} does not exists even though provider has been enabled'.format(p=project_name)
    )

# TODO Add the following test when multi provider marker is implemented

# def test_pause_and_resume_multiple_provider_api(appliance, provider, second_provider, app_creds,
#                                                 soft_assert, request):
