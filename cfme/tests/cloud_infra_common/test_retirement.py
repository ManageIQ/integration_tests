import math
import re
from collections import namedtuple
from datetime import date
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
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.timeutil import parsetime
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


def msg_date_range(expected_dates, fmt):
    """Given the expected_dates dictionary, return a string of the form 'T_1|T_2|...|T_N', where
    T_1 through T_N are datetime strings formatted with '%m/%d/%y %H:%M UTC', one for each unique
    time between the start and end dates.

    Args:
        expected_dates: py:class:`dict` of py:class:`datetime.datetime` instances
        fmt: py:class:`str` format code
    """
    dates = []
    num_min = int(math.ceil((expected_dates['end'] - expected_dates['start']).seconds / 60.0))
    for i in range(num_min):
        next_date = expected_dates['start'] + timedelta(minutes=i)
        next_date = next_date.strftime(fmt)
        dates.append(next_date)
    return "|".join(dates)


def create_vms(template_name, provider, num_vms=1, **deploy_args):
    collection = provider.appliance.provider_based_collection(provider)
    vms = []
    for _ in range(num_vms):
        vm = collection.instantiate(random_vm_name('retire'),
                                    provider,
                                    template_name=template_name)
        vm.create_on_provider(find_in_cfme=True, allow_skip="default", timeout=1200, **deploy_args)
        vms.append(vm)
    return vms


@pytest.fixture(scope="function")
def retire_vm(small_template, provider):
    """Fixture for creating a generic vm/instance

    Args:
        small_template: small template fixture, template on provider
        provider: provider crud object from fixture
    """
    vm = create_vms(small_template.name, provider)[0]
    yield vm
    vm.cleanup_on_provider()


@pytest.fixture(scope="function")
def retire_vm_pair(small_template, provider):
    """Fixture for creating a pair of generic vms/instances

    Args:
        small_template: small template fixture, template on provider
        provider: provider crud object from fixture
    """
    vms = create_vms(small_template.name, provider, 2)
    yield vms
    for vm in vms:
        vm.cleanup_on_provider()


@pytest.fixture(scope="function")
def retire_ec2_s3_vm(s3_template, provider):
    """Fixture for creating an S3 backed paravirtual instance, template is a public ec2 AMI

    Args:
        provider: provider crud object from fixture
    """
    vm = create_vms(s3_template.name, provider, instance_type='m1.small')[0]
    yield vm
    vm.cleanup_on_provider()


def verify_retirement_state(retire_vm, *args):
    """Verify the vm/instance is in the 'retired' state in the UI and assert its power state

    Args:
        retire_vm: vm/instance object
    """
    # wait for the info block showing a date as retired date
    # Use lambda for is_retired since its a property
    view = navigate_to(retire_vm, 'Details')
    assert wait_for(
        lambda: retire_vm.is_retired, delay=5, num_sec=15 * 60,
        fail_func=view.toolbar.reload.click,
        message=f"Wait for VM '{retire_vm.name}' to enter retired state"
    )
    view = retire_vm.load_details()
    power_states = list(args) if args else ['retired']
    assert view.entities.summary('Power Management').get_text_of('Power State') in power_states


def verify_retirement_date(retire_vm, expected_date='Never'):
    """Verify the retirement date for a variety of situations

    Args:
        expected_date: a string, datetime, or a dict datetime dates with 'start' and 'end' keys.
    """
    if isinstance(expected_date, dict):
        expected_date['retire'] = datetime.strptime(retire_vm.retirement_date,
            retire_vm.RETIRE_DATE_FMT)
        logger.info(f'Asserting retirement date "%s" is between "%s" and "%s"',  # noqa
                    expected_date['retire'],
                    expected_date['start'],
                    expected_date['end'])
        assert expected_date['start'] <= expected_date['retire'] <= expected_date['end']
    elif isinstance(expected_date, (parsetime, datetime, date)):
        assert retire_vm.retirement_date == expected_date.strftime(retire_vm.RETIRE_DATE_FMT)
    else:
        assert retire_vm.retirement_date == expected_date


def generate_retirement_date(delta=None):
    """Generate a retirement date that can be used by the VM.retire() method, adding delta

    Args:
        delta: a :py:class: `int` that specifies the number of days to be added to today's date
    Returns: a :py:class: `datetime.date` object including delta as an offset from today
    """
    gen_date = datetime.now().replace(second=0)
    if delta:
        gen_date += timedelta(days=delta)
    return gen_date


def generate_retirement_date_now():
    """Generate a UTC datetime object for now
    Returns: a :py:class: `datetime.datetime` object for the current UTC date + time
    """
    return datetime.utcnow()


@pytest.mark.rhv1
@pytest.mark.meta(automates=[1518926, 1565128])
def test_retirement_now(retire_vm):
    """Tests on-demand retirement of an instance/vm

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h

    Bugzilla:
        1518926
        1565128
    """
    # Assert the Retirement Date is within a window +/- 5 minutes surrounding the actual
    # retirement. Too finicky to get it down to minute precision, nor is it really needed here.
    retire_times = dict()
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-5)

    retire_vm.retire()

    # Verify flash message
    view = retire_vm.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 1 VM and Instance from the CFME Database")

    verify_retirement_state(retire_vm)
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)
    verify_retirement_date(retire_vm, expected_date=retire_times)


@pytest.mark.rhv1
def test_retirement_now_multiple(retire_vm_pair, provider):
    """Tests on-demand retirement of two instances/vms from All VMs page

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    retire_times = {}
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-5)

    # Retire from All VMs/Instances page
    collection = retire_vm_pair[0].parent
    collection.retire(entities=retire_vm_pair)

    # Verify flash message
    view = collection.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 2 VMs and Instances from the CFME Database")

    for vm in retire_vm_pair:
        verify_retirement_state(vm)

    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)

    for vm in retire_vm_pair:
        verify_retirement_date(vm, expected_date=retire_times)


@pytest.mark.provider(gen_func=providers,
                      filters=[ProviderFilter(classes=[EC2Provider],
                                              required_flags=['provision', 'retire'])])
@pytest.mark.parametrize('tagged', [True, False], ids=['tagged', 'untagged'])
def test_retirement_now_ec2_instance_backed(retire_ec2_s3_vm, tagged, appliance):
    """Tests on-demand retirement of an instance/vm

    S3 (instance-backed) EC2 instances that aren't lifecycle tagged won't get shut down

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    # Tag the VM with lifecycle for full retirement based on parameter
    if tagged:
        category = appliance.collections.categories.instantiate(display_name='LifeCycle')
        tag = category.collections.tags.instantiate(
            display_name='Fully retire VM and remove from Provider')
        retire_ec2_s3_vm.add_tag(tag)
        power_states = ['archived']
    else:
        power_states = ['retired']

    # Capture two times to assert the retire time is within a window.
    # Too finicky to get it down to minute precision, nor is it really needed here
    retire_times = dict()
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-5)
    retire_ec2_s3_vm.retire()

    # Verify flash message
    view = retire_ec2_s3_vm.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 1 VM and Instance from the CFME Database")

    verify_retirement_state(retire_ec2_s3_vm, *power_states)
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)
    verify_retirement_date(retire_ec2_s3_vm, expected_date=retire_times)


@pytest.mark.rhv3
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_date(retire_vm, warn):
    """Tests setting retirement date and verifies configured date is reflected in UI

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    num_days = 60
    retire_date = generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(when=retire_date, warn=warn.string)

    # Verify flash message
    view = retire_vm.create_view(retire_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    msg_date = retire_date.strftime(retire_vm.RETIRE_DATE_MSG_FMT)
    view.flash.assert_success_message(f"Retirement date set to {msg_date}")

    verify_retirement_date(retire_vm, expected_date=retire_date)


@pytest.mark.rhv3
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_date_multiple(retire_vm_pair, provider, warn):
    """Tests setting retirement date of multiple VMs, verifies configured date is reflected in
    individual VM Details pages.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    num_days = 60
    retire_date = generate_retirement_date(delta=num_days)

    # Set retirement date from All VMs/Instances page
    collection = retire_vm_pair[0].parent
    collection.set_retirement_date(when=retire_date, warn=warn.string, entities=retire_vm_pair)

    # Verify flash message
    view = collection.create_view(navigator.get_class(collection, 'All').VIEW, wait='5s')
    assert view.is_displayed
    msg_date = retire_date.strftime(retire_vm.RETIRE_DATE_MSG_FMT)
    view.flash.assert_success_message(f"Retirement dates set to {msg_date}")

    for vm in retire_vm_pair:
        verify_retirement_date(vm, expected_date=retire_date)


@pytest.mark.tier(2)
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_offset(retire_vm, warn):
    """Tests setting the retirement by offset

    Minimum is 1 hour, just testing that it is set like test_set_retirement_date

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/15h
    """
    retire_offset = {'months': 0, 'weeks': 2, 'days': 1, 'hours': 3}
    timedelta_offset = retire_offset.copy()
    timedelta_offset.pop('months')  # months not supported in timedelta

    # pad pre-retire timestamp by 60s
    expected_dates = {'start': datetime.utcnow() + timedelta(seconds=-60, **timedelta_offset)}

    retire_vm.set_retirement_date(offset=retire_offset, warn=warn.string)

    # pad post-retire timestamp by 60s
    expected_dates['end'] = datetime.utcnow() + timedelta(seconds=60, **timedelta_offset)

    # Verify flash message
    view = retire_vm.create_view(retire_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    msg_dates = msg_date_range(expected_dates, retire_vm.RETIRE_DATE_MSG_FMT)
    flash_regex = re.compile(f"^Retirement date set to ({msg_dates})$")
    view.flash.assert_success_message(flash_regex)

    verify_retirement_date(retire_vm, expected_date=expected_dates)


@pytest.mark.rhv3
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_offset_multiple(retire_vm_pair, provider, warn):
    """Tests setting retirement date of multiple VMs by offset.
    Verifies configured date is reflected in individual VM Details pages.

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    retire_offset = {'months': 0, 'weeks': 2, 'days': 1, 'hours': 3}
    timedelta_offset = retire_offset.copy()
    timedelta_offset.pop('months')  # months not supported in timedelta

    # pad pre-retire timestamp by 60s
    expected_dates = {'start': datetime.utcnow() + timedelta(seconds=-60, **timedelta_offset)}

    collection = retire_vm_pair[0].parent
    collection.set_retirement_date(offset=retire_offset, warn=warn.string, entities=retire_vm_pair)

    # pad post-retire timestamp by 60s
    expected_dates['end'] = datetime.utcnow() + timedelta(seconds=60, **timedelta_offset)

    # Verify flash message
    view = collection.create_view(navigator.get_class(collection, 'All').VIEW, wait='5s')
    assert view.is_displayed
    msg_dates = msg_date_range(expected_dates, retire_vm_pair[0].RETIRE_DATE_MSG_FMT)
    flash_regex = re.compile(f"^Retirement dates set to ({msg_dates})$")
    view.flash.assert_success_message(flash_regex)

    for vm in retire_vm_pair:
        verify_retirement_date(vm, expected_date=expected_dates)


@pytest.mark.rhv3
def test_unset_retirement_date(retire_vm):
    """Tests cancelling a scheduled retirement by removing the set date

    Polarion:
        assignee: tpapaioa
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    num_days = 3
    retire_date = generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(when=retire_date)

    # Verify flash message
    view = retire_vm.create_view(retire_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    msg_date = retire_date.strftime(retire_vm.RETIRE_DATE_MSG_FMT)
    view.flash.assert_success_message(f"Retirement date set to {msg_date}")

    verify_retirement_date(retire_vm, expected_date=retire_date)

    retire_vm.set_retirement_date(when=None)

    # Verify flash message
    view = retire_vm.create_view(retire_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    view.flash.assert_success_message("Retirement date removed")

    verify_retirement_date(retire_vm, expected_date='Never')


@pytest.mark.rhv3
@pytest.mark.tier(2)
@pytest.mark.parametrize('remove_date', [True, False], ids=['remove_date', 'set_future_date'])
def test_resume_retired_instance(retire_vm, provider, remove_date):
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

    retire_vm.retire()

    # Verify flash message
    view = retire_vm.create_view(RequestsView)
    assert view.is_displayed
    view.flash.assert_success_message(
        "Retirement initiated for 1 VM and Instance from the CFME Database")

    verify_retirement_state(retire_vm)

    retire_date = None if remove_date else generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(when=retire_date)

    # Verify flash message
    view = retire_vm.create_view(retire_vm.DETAILS_VIEW_CLASS, wait='5s')
    assert view.is_displayed
    if retire_date:
        msg_date = retire_date.strftime(retire_vm.RETIRE_DATE_MSG_FMT)
        view.flash.assert_success_message(f"Retirement date set to {msg_date}")
    else:
        view.flash.assert_success_message("Retirement date removed")

    verify_retirement_date(retire_vm, expected_date=retire_date if retire_date else 'Never')
    assert not retire_vm.is_retired


@pytest.mark.tier(2)
@pytest.mark.long_running
@test_requirements.multi_region
@test_requirements.retirement
def test_vm_retirement_from_global_region(setup_multi_region_cluster,
                                          multi_region_cluster,
                                          activate_global_appliance,
                                          setup_remote_provider,
                                          retire_vm):
    """
    retire a vm via CA

    Polarion:
        assignee: izapolsk
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
    retire_times = dict()
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-5)
    retire_vm.retire()
    verify_retirement_state(retire_vm)
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)
    verify_retirement_date(retire_vm, expected_date=retire_times)


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.long_running
@test_requirements.multi_region
@test_requirements.retirement
def test_vm_retirement_from_global_region_via_rest():
    """
    retire a vm via CA

    Polarion:
        assignee: izapolsk
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
