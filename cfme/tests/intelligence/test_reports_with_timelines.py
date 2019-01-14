# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.control.explorer import policies
from cfme.tests.cloud_infra_common.test_events import vm_crud
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2),
    pytest.mark.provider([InfraProvider], required_fields=['provisioning'], scope='module')
]

PATHS = [
        ["Events", "Policy", "Policy Events for Last Week"],
        ["Events", "Policy", "Policy Events for the Last 7 Days"],
        ["Configuration Management", "Hosts", "Date brought under Management for Last Week"],
        ["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
    ]

UPDATES = [
         {'filter':
             {'primary_filter':"fill_field(Policy Event : Activity Sample - Timestamp (Day/Time), "
                "IS, This Week)"},
         },
         {'report_fields': ["Activity Sample - Timestamp (Day/Time)",
            "Miq Policy Sets : Date Created", "Miq Policy Sets : Date Updated",
            "Miq Policy Sets : Description", "Miq Policy Sets : EVM Unique ID (Guid)"
            ],
          'filter':
             {'primary_filter':"fill_field(Policy Event : Activity Sample - Timestamp (Day/Time), "
                "IS, This Week)"},
         },
         {'filter':
              {'primary_filter':"fill_field(Host / Node : Date Created, IS, This Week)"}
         },
         {'filter':
             {'primary_filter':"fill_field(Event Stream.Host / Node : Total VMs, >, 0)"}
         },

    ]

@pytest.fixture(scope="function")
def setup_for_reports():
    """ wrapper function for _setup_for_reports, so that it runs during test

    Returns:
        unbound function object for calling during the test
    """
    def _setup_for_reports(request, appliance, provider, path, updates, vm_crud, register_event):
        """ This function makes copies of the default reports so that we can test the timelines
        on the CloudIntel->Timelines page

        Args:
            request: py.test funcarg request
            appliance: IPAppliance object
            provider: provider object
            path: path to the report in the tree
            updates: updates to the default report so that it will display events
            vm_crud: vm for Policy events
            register_event: function for registering events
            args: kwargs for extra_steps
        """
        # first perform extra steps for Policy stuff
        if "Policy" in path:
            generate_policy_event(request, appliance, provider, vm_crud, register_event)
        report = appliance.collections.reports.instantiate(
            type=path[0], subtype=path[1], menu_name=path[2]
        )
        # copy the default report
        copied_report = report.copy()
        # update the copied report
        copied_report.update(updates)
        # delete report at end of test
        request.addfinalizer(copied_report.delete)

        return copied_report

    return _setup_for_reports


def generate_policy_event(request, appliance, provider, vm_crud, register_event):
    # create necessary objects
    action = appliance.collections.actions.create(
        fauxfactory.gen_alpha(),
        "Tag",
        dict(tag=("My Company Tags", "Environment", "Development")))
    request.addfinalizer(action.delete)

    policy = appliance.collections.policies.create(
        policies.VMControlPolicy,
        fauxfactory.gen_alpha()
    )
    request.addfinalizer(policy.delete)

    policy.assign_events("VM Create Complete")
    request.addfinalizer(policy.assign_events)
    policy.assign_actions_to_event("VM Create Complete", action)

    profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alpha(), policies=[policy])
    request.addfinalizer(profile.delete)

    # assign the policy profile to the provider
    provider.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: provider.unassign_policy_profiles(profile.description))

    register_event(target_type='VmOrTemplate', target_name=vm_crud.name,
                   event_type='vm_create')

    vm_crud.create_on_provider(find_in_cfme=True)


@pytest.mark.parametrize("path, updates", zip(PATHS, UPDATES))
def test_reports_with_timelines(request, appliance, provider, path, updates, setup_for_reports,
                                vm_crud, register_event):
    """
    Test that a timeline widget is displayed for a reports.
    Note that since the default reports look at last week, to test, we modify the reports

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/5h
        casecomponent: web_ui
        caseimportance: medium
        testSteps:
            1. Add an infrastructure provider to ensure that an event for each report will occur
            2. Navigate to Cloud Intel -> Reports
            3. Modify one of the default reports to display events from today
            4. Navigate to Cloud Intel -> Timelines
            5. Click on the report you created
            6. Verify that the timeline (with events) is properly displayed
    """
    copied_report = setup_for_reports(request, appliance, provider, path, updates,
                                      vm_crud, register_event)
    # navigate to timeline for this report
    view = navigate_to(copied_report, 'Timeline')
    # assert that at least 1 event is present on the timeline chart
    assert len(view.chart.get_events()) > 0
