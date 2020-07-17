import math
import re
from collections import namedtuple
from datetime import datetime
from datetime import timedelta

import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import providers
from cfme.services.requests import RequestsView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.long_running,
    test_requirements.retirement,
    pytest.mark.provider([CloudProvider, InfraProvider],
                         required_flags=['provision', 'retire']),
]


RetirementWarning = namedtuple('RetirementWarning', ['id', 'string'])

warnings = [
    RetirementWarning('no_warning', 'None'),
    RetirementWarning('1_week_warning', '1 Week before retirement'),
    RetirementWarning('2_week_warning', '2 Weeks before retirement'),
    RetirementWarning('30_day_warning', '30 Days before retirement')]


def msg_date_range(expected_date, fmt):
    """Given the expected_date dictionary, return a string of the form 'T_1|T_2|...|T_N', where
    T_1 through T_N are formatted datetime strings, one for each unique time between the start
    and end dates (to minute resolution).

    Args:
        expected_date: py:class:`dict` of py:class:`datetime.datetime` instances
        fmt: py:class:`str` datetime format string
    """
    times = []
    start = expected_date.get('start')
    end = expected_date.get('end')

    assert isinstance(start, datetime) and isinstance(end, datetime)

    num_min = int(math.ceil((end - start).seconds / 60.0))
    for i in range(num_min):
        s = (start + timedelta(minutes=i)).strftime(fmt)
        times.append(s)
    return "|".join(times)


def verify_retirement_state(vm, *args):
    """Verify the VM/Instance is in the 'retired' state in the UI, and assert its power state.

    Args:
        vm: VM/Instance object
      args: (optional) one or more :py:class:`str` corresponding to the Power State(s)
            that the VM/Ibstance can have once retired. If not specified, then the default
            value of 'retired' will be used.
    """
    # Wait for the info block showing a Retirement Date.
    # Use lambda for is_retired since it's a property.
    view = navigate_to(vm, 'Details')
    assert wait_for(
        lambda: vm.is_retired, delay=5, num_sec=15 * 60,
        fail_func=view.toolbar.reload.click,
        message=f"Wait for VM '{vm.name}' to enter retired state"
    )
    view = vm.load_details()
    power_states = list(args) if args else ['retired']
    assert view.entities.summary('Power Management').get_text_of('Power State') in power_states


def verify_retirement_date(vm, expected_date='Never'):
    """Verify the retirement date for a variety of situations.

    Args:
        vm: VM/Instance object
        expected_date:
            :py:class:`str`
            or :py:class:`datetime`
            or :py:class:`dict`:
                'start': :py:class:`datetime`
                'end': :py:class:`datetime`
    """
    if isinstance(expected_date, dict):
        expected_date['retire'] = datetime.strptime(vm.retirement_date, vm.RETIRE_DATE_FMT)
        logger.info(f'Asserting retirement date "%s" is between "%s" and "%s"',  # noqa
                    expected_date['retire'],
                    expected_date['start'],
                    expected_date['end'])
        assert expected_date['start'] <= expected_date['retire'] <= expected_date['end']
    elif isinstance(expected_date, datetime):
        assert vm.retirement_date == expected_date.strftime(vm.RETIRE_DATE_FMT)
    else:
        assert vm.retirement_date == expected_date


def generate_retirement_date(delta=9):
    """Generate a retirement date that can be used by the VM.retire() method, adding delta.

    Args:
        delta: a :py:class: `int` that specifies the number of days to be added to today's date

    Returns:
         a :py:class: `datetime.date` object including delta as an offset from today
    """
    gen_date = datetime.now().replace(second=0)
    if delta:
        gen_date += timedelta(days=delta)
    return gen_date


@pytest.mark.meta(automates=[1518926, 1565128])
def test_retirement_now(create_vm):
    """Test on-demand retirement of a VM/Instance.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h

    Bugzilla:
        1518926
        1565128
    """
    # Assert the Retirement Date is within a window +/- 5 minutes surrounding the actual
    # retirement.
    expected_date = {}
    expected_date['start'] = datetime.utcnow() + timedelta(minutes=-5)

    create_vm.retire()

    # Verify flash message
    view = create_vm.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 1 VM and Instance from the CFME Database")

    verify_retirement_state(create_vm)
    expected_date['end'] = datetime.utcnow() + timedelta(minutes=5)
    verify_retirement_date(create_vm, expected_date=expected_date)


@pytest.mark.parametrize('create_vms',
                         [{'template_type': 'small_template', 'num_vms': 2}],
                         ids=['small_template-two_vms'],
                         indirect=True)
def test_retirement_now_multiple(create_vms, provider):
    """Tests on-demand retirement of two VMs/Instances from All VMs or All Instances page.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    expected_date = {}
    expected_date['start'] = datetime.utcnow() + timedelta(minutes=-5)

    # Retire from All VMs or All Instances page
    collection = create_vms[0].parent
    collection.retire(entities=create_vms)

    # Verify flash message.
    view = collection.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 2 VMs and Instances from the CFME Database")

    for vm in create_vms:
        verify_retirement_state(vm)

    expected_date['end'] = datetime.utcnow() + timedelta(minutes=5)

    for vm in create_vms:
        verify_retirement_date(vm, expected_date=expected_date)


@pytest.mark.provider(gen_func=providers,
                      filters=[ProviderFilter(classes=[EC2Provider],
                                              required_flags=['provision', 'retire'])])
@pytest.mark.parametrize('tagged', [True, False], ids=['tagged', 'untagged'])
@pytest.mark.parametrize('create_vm', ['s3_template'], indirect=True)
def test_retirement_now_ec2_instance_backed(create_vm, tagged, appliance):
    """Test on-demand retirement of an S3 (instance-backed) EC2 instance.
    Tagged instances should be removed from the provider and become Archived.
    Untagged instances should not be removed from the provider.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    if tagged:
        category = appliance.collections.categories.instantiate(display_name='LifeCycle')
        tag = category.collections.tags.instantiate(
            display_name='Fully retire VM and remove from Provider')
        create_vm.add_tag(tag)
        power_states = ['archived']
    else:
        power_states = ['retired']

    # Capture two times to assert the retire time is within a window.
    expected_date = {}
    expected_date['start'] = datetime.utcnow() + timedelta(minutes=-5)

    create_vm.retire()

    # Verify flash message.
    view = create_vm.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 1 VM and Instance from the CFME Database")

    verify_retirement_state(create_vm, *power_states)
    expected_date['end'] = datetime.utcnow() + timedelta(minutes=5)
    verify_retirement_date(create_vm, expected_date=expected_date)


@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_date(create_vm, warn):
    """Tests setting retirement date and verifies configured date is reflected in UI

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    num_days = 60
    expected_date = generate_retirement_date(delta=num_days)

    create_vm.set_retirement_date(when=expected_date, warn=warn.string)

    # Verify flash message
    view = create_vm.create_view(create_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    msg_date = expected_date.strftime(create_vm.RETIRE_DATE_MSG_FMT)
    view.flash.assert_success_message(f"Retirement date set to {msg_date}")

    verify_retirement_date(create_vm, expected_date=expected_date)


@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
@pytest.mark.parametrize('create_vms',
                         [{'template_type': 'small_template', 'num_vms': 2}],
                         ids=['small_template-two_vms'],
                         indirect=True)
def test_set_retirement_date_multiple(create_vms, provider, warn):
    """Tests setting retirement date of multiple VMs, verifies configured date is reflected in
    individual VM Details pages.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    num_days = 60
    expected_date = generate_retirement_date(delta=num_days)

    # Set retirement date from All VMs or All Instances page.
    collection = create_vms[0].parent
    collection.set_retirement_date(entities=create_vms, when=expected_date, warn=warn.string)

    # Verify flash message.
    view = collection.create_view(navigator.get_class(collection, 'All').VIEW, wait='5s')
    assert view.is_displayed
    msg_date = expected_date.strftime(create_vms[0].RETIRE_DATE_MSG_FMT)
    view.flash.assert_success_message(f"Retirement dates set to {msg_date}")

    for vm in create_vms:
        verify_retirement_date(vm, expected_date=expected_date)


@pytest.mark.tier(2)
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_offset(create_vm, warn):
    """Tests setting the retirement date with the 'Time Delay from Now' option.
    Minimum is 1 hour, just testing that it is set like test_set_retirement_date.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/15h
    """
    retire_offset = {'months': 0, 'weeks': 2, 'days': 1, 'hours': 3}
    timedelta_offset = retire_offset.copy()
    timedelta_offset.pop('months')  # months not supported in timedelta

    expected_date = {}
    # Pad pre-retirement timestamp by 60s.
    expected_date['start'] = datetime.utcnow() + timedelta(seconds=-60, **timedelta_offset)

    create_vm.set_retirement_date(offset=retire_offset, warn=warn.string)

    # Pad post-retirement timestamp by 60s.
    expected_date['end'] = datetime.utcnow() + timedelta(seconds=60, **timedelta_offset)

    # Verify flash message.
    view = create_vm.create_view(create_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    msg_dates = msg_date_range(expected_date, create_vm.RETIRE_DATE_MSG_FMT)
    flash_regex = re.compile(f"^Retirement date set to ({msg_dates})$")
    view.flash.assert_success_message(flash_regex)

    verify_retirement_date(create_vm, expected_date=expected_date)


@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
@pytest.mark.parametrize('create_vms',
                         [{'template_type': 'small_template', 'num_vms': 2}],
                         ids=['small_template-two_vms'],
                         indirect=True)
def test_set_retirement_offset_multiple(create_vms, provider, warn):
    """Test setting the retirement date of multiple VMs/Instances using 'Time Delay from Now'
    option. Verify the selected retirement date is reflected in each VM's/Instance's Details
    page.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    retire_offset = {'months': 0, 'weeks': 2, 'days': 1, 'hours': 3}
    timedelta_offset = retire_offset.copy()
    timedelta_offset.pop('months')  # months not supported in timedelta

    expected_date = {}

    # Pad pre-retirement timestamp by 60s.
    expected_date['start'] = datetime.utcnow() + timedelta(seconds=-60, **timedelta_offset)

    collection = create_vms[0].parent
    collection.set_retirement_date(entities=create_vms, offset=retire_offset, warn=warn.string)

    # Pad post-retirement timestamp by 60s.
    expected_date['end'] = datetime.utcnow() + timedelta(seconds=60, **timedelta_offset)

    # Verify flash message
    view = collection.create_view(navigator.get_class(collection, 'All').VIEW, wait='5s')
    assert view.is_displayed
    msg_dates = msg_date_range(expected_date, create_vms[0].RETIRE_DATE_MSG_FMT)
    flash_regex = re.compile(f"^Retirement dates set to ({msg_dates})$")
    view.flash.assert_success_message(flash_regex)

    for vm in create_vms:
        verify_retirement_date(vm, expected_date=expected_date)


def test_unset_retirement_date(create_vm):
    """Tests cancelling a scheduled retirement by removing the set date

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    num_days = 3
    retire_date = generate_retirement_date(delta=num_days)
    create_vm.set_retirement_date(when=retire_date)

    # Verify flash message
    view = create_vm.create_view(create_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    msg_date = retire_date.strftime(create_vm.RETIRE_DATE_MSG_FMT)
    view.flash.assert_success_message(f"Retirement date set to {msg_date}")

    verify_retirement_date(create_vm, expected_date=retire_date)

    create_vm.set_retirement_date(when=None)

    # Verify flash message.
    view = create_vm.create_view(create_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    view.flash.assert_success_message("Retirement date removed")

    verify_retirement_date(create_vm, expected_date='Never')


@pytest.mark.tier(2)
@pytest.mark.parametrize('remove_date', [True, False], ids=['remove_date', 'set_future_date'])
def test_resume_retired_instance(create_vm, provider, remove_date):
    """Test resuming a retired instance, should be supported for infra and cloud, though the
    actual recovery results may differ depending on state after retirement

    Two methods to resume:
    1. Set a retirement date in the future
    2. Remove the set retirement date

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/2h
    """
    num_days = 5

    create_vm.retire()

    # Verify flash message.
    view = create_vm.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 1 VM and Instance from the CFME Database")

    verify_retirement_state(create_vm)

    retire_date = None if remove_date else generate_retirement_date(delta=num_days)
    create_vm.set_retirement_date(when=retire_date)

    # Verify flash message.
    view = create_vm.create_view(create_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    if retire_date:
        msg_date = retire_date.strftime(create_vm.RETIRE_DATE_MSG_FMT)
        view.flash.assert_success_message(f"Retirement date set to {msg_date}")
    else:
        view.flash.assert_success_message("Retirement date removed")

    verify_retirement_date(create_vm, expected_date=retire_date if retire_date else 'Never')
    assert not create_vm.is_retired


@pytest.mark.tier(2)
@pytest.mark.long_running
@test_requirements.multi_region
@test_requirements.retirement
@pytest.mark.meta(automates=[1839770])
def test_vm_retirement_from_global_region(replicated_appliances, create_vm):
    """
    Retire a VM via Centralized Administration

    Bugzilla:
        1839770

    Polarion:
        assignee: tpapaioa
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/3h
        testSteps:
            1. Have a VM created in the provider in the Remote region
               subscribed to Global.
            2. Retire the VM using the Global appliance.
        expectedResults:
            1.
            2. VM transitions to Retired state in the Global and Remote region.

    """
    remote_appliance, global_appliance = replicated_appliances

    expected_date = {}
    expected_date['start'] = datetime.utcnow() + timedelta(minutes=-5)

    provider = create_vm.provider

    # Instantiate on each appliance so that browser uses the correct appliance.
    vm_per_appliance = {
        a: a.provider_based_collection(provider).instantiate(create_vm.name, provider)
        for a in replicated_appliances
    }

    with remote_appliance:
        provider.create()

    with global_appliance:
        vm_per_appliance[global_appliance].retire()

    with remote_appliance:
        verify_retirement_state(vm_per_appliance[remote_appliance])
        expected_date['end'] = datetime.utcnow() + timedelta(minutes=5)
        verify_retirement_date(vm_per_appliance[remote_appliance], expected_date=expected_date)


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.long_running
@test_requirements.multi_region
@test_requirements.retirement
def test_vm_retirement_from_global_region_via_rest():
    """
    retire a vm via CA

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Provisioning
        initialEstimate: 1/3h
        testSteps:
            1. Have a VM created in the provider in the Remote region
               subscribed to Global.
            2. Retire the VM using the Global appliance.
        expectedResults:
            1.
            2. VM transitions to Retired state in the Global and Remote region.

    """
    pass
