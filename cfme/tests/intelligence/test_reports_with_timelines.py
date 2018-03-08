import fauxfactory
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.vm import VM
from cfme.control.explorer.policies import VMControlPolicy
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for

all_prov = ProviderFilter(classes=[InfraProvider, CloudProvider])
excluded = ProviderFilter(classes=[GCEProvider, SCVMMProvider, OpenStackProvider],
                          inverted=True)
pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.provider(gen_func=providers, filters=[excluded, all_prov]),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture
def new_vm(provider):
    vm = VM.factory(random_vm_name('timelines', max_length=16), provider)
    vm.create_on_provider(find_in_cfme=True)
    logger.info('Fixture new_vm set up! Name: %r Provider: %r', vm.name, vm.provider.name)
    yield vm
    vm.cleanup_on_provider()


@pytest.fixture
def control_policy(appliance, new_vm):
    action = appliance.collections.actions.create(fauxfactory.gen_alpha(),
                                                  "Tag", dict(tag=("My Company Tags",
                                                                   "Environment",
                                                                   "Development")))
    policy = appliance.collections.policies.create(VMControlPolicy, fauxfactory.gen_alpha())
    policy.assign_events("VM Power Off")
    policy.assign_actions_to_event("VM Power Off", action)
    profile = appliance.collections.policy_profiles.create(fauxfactory.gen_alpha(),
                                                           policies=[policy])

    yield new_vm.assign_policy_profiles(profile.description)
    if profile.exists:
        profile.delete()
    if policy.exists:
        policy.delete()
    if action.exists:
        action.delete()


@pytest.fixture
def report_policy_event_week(appliance):
    param_dict = {
        "menu_name": "Policy Events for This Week",
        "title": "Policy Events for This Week",
        "base_report_on": "Policy Events",
        "cancel_after": "2 Hours",
        "report_fields": ["Target Name", "Event Type", "Activity Sample - Timestamp (Day/Time)",
                          "Miq Event Definition Description", "Miq Policy Description"],
        "filter": {"primary_filter": "fill_field(field=Policy Event : Activity Sample - "
                                     "Timestamp (Day/Time), value=This Week);"},
        "timeline": {"based_on": "Activity Sample - Timestamp (Day/Time)"}
    }
    report = appliance.collections.reports.create(**param_dict)
    yield report
    if report.exists:
        report.delete()


@pytest.fixture
def report_policy_7_days(appliance):
    param_dict = {
        "menu_name": "report policy 7 days",
        "title": "report policy 7 days",
        "base_report_on": "Management Events",
        "cancel_after": "2 Hours",
        "report_fields": ["VM Name",
                          "Event Type",
                          "Source",
                          "Parent Host",
                          "Date Created"
                          ],
        "filter": {"primary_filter": "fill_field(field=Management Event : Date Created, "
                                     "value=This Week);"},
        "timeline": {"based_on": "Date Created"}
    }
    report = appliance.collections.reports.create(**param_dict)
    yield report
    if report.exists:
        report.delete()


@pytest.fixture
def report_power_operations(appliance):
    param_dict = {
        "menu_name": "VMs Powered On/Off this week",
        "title": "VMs Powered On/Off this week",
        "base_report_on": "Management Events",
        "cancel_after": "2 Hours",
        "report_fields": ["VM Name",
                          "Event Type",
                          "Source",
                          "Parent Host",
                          "Date Created"
                          ],
        "filter": {"primary_filter": "fill_field(field=Management Event : Activity Sample - "
                                     "Timestamp (Day/Time), key=IS, value=This Week);"},
        "timeline": {"based_on": "Date Created"},

    }
    report = appliance.collections.reports.create(**param_dict)
    yield report
    if report.exists:
        report.delete()


@pytest.fixture
def report_hosts_data_management(appliance):
    param_dict = {
        "menu_name": "host data management",
        "title": "host data management",
        "base_report_on": "Management Events",
        "cancel_after": "2 Hours",
        "report_fields": ["VM Name",
                          "Event Type",
                          "Source",
                          "Parent Host",
                          "Date Created"
                          ],
        "filter": {"primary_filter": "fill_field(field=Management Event.Host / Node : Date Created,"
                                     "key=IS, value=This Month);"},
        "timeline": {"based_on": "Date Created"}
    }
    report = appliance.collections.reports.create(**param_dict)
    yield report
    if report.exists:
        report.delete()


def check_timeline(vm, view, check_func):
    events_list = view.chart.get_events()
    logger.info('events_list: %r', str(events_list))
    if not events_list:
        return False

    found_events = []

    for evt in events_list:
        if check_func:
            found_events.append(evt)
            break

    logger.info('found events: %r', str(found_events))
    return bool(found_events)


def test_custom_report_policy_timeline(new_vm, control_policy, report_policy_event_week):
    """Create a policy event and assign it to the VM, stop the vm and verify that the policy
    policy events appears in the cloud intel report timelines. the report is a copy of one
    existing in Reports"""
    logger.info('Will stop VM %r', new_vm.name)
    wait_for(new_vm.provider.mgmt.stop_vm, [new_vm.name], timeout='7m',
             message='Stopping VM failed')
    view = navigate_to(report_policy_event_week, 'Timelines')
    assert view.is_timeline_displayed, 'Timeline is not displayed.'
    view.flash.assert_no_error()

    wait_for(check_timeline,
             [new_vm,
              view,
              lambda evt: hasattr(evt, 'target_name') and evt.target_name == new_vm.name and
              evt.assigned_profiles in new_vm.assigned_policy_profiles
              ],
             timeout='5m',
             fail_func=lambda: navigate_to(report_policy_event_week, 'Timelines'),
             message='event of {} not found on report {}'.format(new_vm.name,
                                                                 report_policy_event_week.title))


@pytest.mark.meta(blockers=[BZ(1563823, forced_streams=['5.9'])])
def test_custom_report_policy_7_days_timeline(new_vm, control_policy, report_policy_7_days):
    """Create a policy event and assign it to the VM, stop the vm and verify that the policy
    policy events appears in the cloud intel report timelines. the report is a copy of one
    existing in Reports"""
    logger.info('Will stop VM %r', new_vm.name)
    wait_for(new_vm.provider.mgmt.stop_vm, [new_vm.name], timeout='7m',
             message='Stopping VM failed')
    view = navigate_to(report_policy_7_days, 'Timelines')
    assert view.is_timeline_displayed, 'Timeline is not displayed.'
    view.flash.assert_no_error()

    wait_for(check_timeline,
             [new_vm,
              view,
              lambda evt: hasattr(evt, 'vm_or_template') and (evt.vm_or_template == new_vm.name and
                          evt.assigned_profiles in new_vm.assigned_policy_profiles)
              ],
             timeout='5m',
             fail_func=lambda: navigate_to(report_policy_7_days, 'Timelines'),
             message='event of {} not found on report {}'.format(new_vm.name,
                                                                 report_policy_7_days.title))


def test_custom_report_power_operations_timeline(new_vm, report_power_operations):
    """Create a report which list the power events and verify that the VM stop event is found in
    the cloud intel timeline."""
    logger.info('Will stop VM %r', new_vm.name)
    wait_for(new_vm.provider.mgmt.stop_vm, [new_vm.name], timeout='7m',
             message='Stopping VM failed')

    view = navigate_to(report_power_operations, 'Timelines')
    assert view.is_timeline_displayed, 'Timeline is not displayed.'
    view.flash.assert_no_error()

    wait_for(check_timeline,
             [new_vm,
              view,
              lambda evt: hasattr(evt, 'vm_name') and evt.vm_name == new_vm.name and evt.event_type
              in ('vm_poweroff', 'VmPoweredOffEvent', 'USER_STOP_VM', 'AWS_API_CALL_StopInstances',
                  'AWS_EC2_Instance_stopped', 'virtualMachines_deallocate_EndRequest')
              ],
             timeout='5m',
             fail_func=lambda: navigate_to(report_power_operations, 'Timelines'),
             message='event of {} not found on report {}'.format(new_vm.name,
                                                                 report_power_operations.title))


@pytest.mark.meta(blockers=[BZ(1571207, forced_streams=['5.9'],
                            unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.uncollectif(lambda provider: provider.one_of(CloudProvider), reason='Only for infra')
def test_custom_report_hosts_data_management_timeline(new_vm, report_hosts_data_management):
    """ Create a report of host data and verify that the stop event is reported on the host and
    visible on its cloud intel timeline."""
    logger.info('Will stop VM %r', new_vm.name)
    wait_for(new_vm.provider.mgmt.stop_vm, [new_vm.name], timeout='7m',
             message='Stopping VM failed')
    view = navigate_to(report_hosts_data_management, 'Timelines')
    assert view.is_timeline_displayed, 'Timeline is not displayed.'
    view.flash.assert_no_error()

    wait_for(check_timeline,
             [new_vm,
              view,
              lambda evt: hasattr(evt, 'vm_name') and evt.vm_name == new_vm.name and
              (new_vm.host.name == evt.parent_host or evt.name)
              ],
             timeout='5m',
             fail_func=lambda: navigate_to(report_hosts_data_management, 'Timelines'),
             message='event of {} not found on {}'.format(new_vm.name,
                                                          report_hosts_data_management.title))
