# -*- coding: utf-8 -*-
from collections import namedtuple
from datetime import date, timedelta, datetime

import pytest

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.common.provider import CloudInfraProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.timeutil import parsetime
from cfme.utils.wait import wait_for
from cfme.markers.env_markers.provider import providers

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.long_running,
    test_requirements.retirement,
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[CloudInfraProvider],
                                                 required_flags=['provision', 'retire'])]),
]


RetirementWarning = namedtuple('RetirementWarning', ['id', 'string'])

warnings = [
    RetirementWarning('no_warning', 'None'),
    RetirementWarning('1_week_warning', '1 Week before retirement'),
    RetirementWarning('2_week_warning', '2 Weeks before retirement'),
    RetirementWarning('30_day_warning', '30 Days before retirement')]


@pytest.yield_fixture(scope="function")
def retire_vm(small_template, provider):
    """Fixture for creating a generic vm/instance

    Args:
        small_template: small template fixture, template on provider
        provider: provider crud object from fixture
    """
    vm = VM.factory(random_vm_name('retire'), provider, template_name=small_template.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default", timeout=1200)
    yield vm
    vm.cleanup_on_provider()

@pytest.yield_fixture(scope="function")
def retire_ec2_s3_vm(provider):
    """Fixture for creating an S3 backed paravirtual instance, template is a public ec2 AMI

    Args:
        provider: provider crud object from fixture
    """
    vm = VM.factory(random_vm_name('retire'), provider,
                    template_name='amzn-ami-pv-2015.03.rc-1.x86_64-s3')
    vm.create_on_provider(find_in_cfme=True, allow_skip="default", timeout=1200)
    yield vm
    vm.cleanup_on_provider()

def verify_retirement_state(retire_vm):
    """Verify the vm/instance is in the 'retired' state in the UI and assert its power state

    Args:
        retire_vm: vm/instance object
    """
    # wait for the info block showing a date as retired date
    # Use lambda for is_retired since its a property
    view_cls = navigator.get_class(retire_vm, 'Details').VIEW
    view = retire_vm.appliance.browser.create_view(view_cls)
    assert wait_for(
        lambda: retire_vm.is_retired, delay=5, num_sec=15 * 60,
        fail_func=view.toolbar.reload.click,
        message="Wait for VM '{}' to enter retired state".format(retire_vm.name)
    )

    retirement_states = ['off', 'suspended', 'unknown', 'terminated']
    view = retire_vm.load_details()
    assert view.entities.summary('Power Management').get_text_of('Power State') in retirement_states


def verify_retirement_date(retire_vm, expected_date='Never'):
    """Verify the retirement date for a variety of situations

    Args:
        expected_date: a string, datetime, or a dict datetime dates with 'start' and 'end' keys.
    """
    if isinstance(expected_date, dict):
        # convert to a parsetime object for comparsion, function depends on version
        if 'UTC' in VM.RETIRE_DATE_FMT.pick(retire_vm.appliance.version):
            convert_func = parsetime.from_american_minutes_with_utc
        elif VM.RETIRE_DATE_FMT.pick(retire_vm.appliance.version).endswith('+0000'):
            convert_func = parsetime.from_saved_report_title_format
        else:
            convert_func = parsetime.from_american_date_only
        expected_date.update({'retire': convert_func(retire_vm.retirement_date)})
        logger.info('Asserting retire date "%s" is between "%s" and "%s"',  # noqa
                    expected_date['retire'],
                    expected_date['start'],
                    expected_date['end'])

        assert expected_date['start'] <= expected_date['retire'] <= expected_date['end']

    elif isinstance(expected_date, (parsetime, datetime, date)):
        assert retire_vm.retirement_date == expected_date.strftime(
            VM.RETIRE_DATE_FMT.pick(retire_vm.appliance.version))
    else:
        assert retire_vm.retirement_date == expected_date


def generate_retirement_date(delta=None):
    """Generate a retirement date that can be used by the VM.retire() method, adding delta

    Args:
        delta: a :py:class: `int` that will be added to today's date
    Returns: a :py:class: `datetime.date` object including delta as an offset from today
    """
    gen_date = date.today()
    if delta:
        gen_date += timedelta(days=delta)
    return gen_date


def generate_retirement_date_now():
    """Generate a UTC datetime object for now
    Returns: a :py:class: `datetime.datetime` object for the current UTC date + time
    """
    return datetime.utcnow()


@pytest.mark.rhv1
def test_retirement_now(retire_vm):
    """Tests on-demand retirement of an instance/vm
    """
    # For 5.7 capture two times to assert the retire time is within a window.
    # Too finicky to get it down to minute precision, nor is it really needed here
    retire_times = dict()
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-5)
    retire_vm.retire()
    verify_retirement_state(retire_vm)
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)
    verify_retirement_date(retire_vm, expected_date=retire_times)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(EC2Provider),
                         reason='Only valid for EC2 provider')
@pytest.mark.parametrize('tagged', [True, False], ids=['tagged', 'untagged'])
def test_retirement_now_ec2_instance_backed(retire_ec2_s3_vm, tagged):
    """Tests on-demand retirement of an instance/vm

    S3 (instance-backed) EC2 instances that aren't lifecycle tagged won't get shut down
    """
    # Tag the VM with lifecycle for full retirement based on parameter
    if tagged:
        retire_ec2_s3_vm.add_tag('LifeCycle', 'Fully retire VM and remove from Provider')
        expected_power_state = ['terminated']
    else:
        # no tagging
        expected_power_state = ['on']

    # For 5.7+ capture two times to assert the retire time is within a window.
    # Too finicky to get it down to minute precision, nor is it really needed here
    retire_times = dict()
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-5)
    retire_ec2_s3_vm.retire()
    view_cls = navigator.get_class(retire_ec2_s3_vm, 'Details').VIEW
    reload = retire_ec2_s3_vm.appliance.browser.create_view(view_cls).toolbar.reload
    assert wait_for(lambda: retire_ec2_s3_vm.is_retired,
                    delay=5, num_sec=10 * 60, fail_func=reload.click,
                    message="Wait for VM '{}' to enter retired state"
                    .format(retire_ec2_s3_vm.name))
    view = retire_ec2_s3_vm.load_details()
    assert view.entities.power_management.get_text_of('Power State') in expected_power_state
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)
    verify_retirement_date(retire_ec2_s3_vm, expected_date=retire_times)


@pytest.mark.rhv3
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_date(retire_vm, warn):
    """Tests setting retirement date and verifies configured date is reflected in UI

    Note we cannot control the retirement time, just day, so we cannot wait for the VM to retire
    """
    # TODO retirement supports datetime (no tz) in gaprindashvili/59z, update accordingly
    num_days = 2
    retire_date = generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(retire_date, warn=warn.string)
    verify_retirement_date(retire_vm, expected_date=retire_date)


@pytest.mark.tier(2)
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
@pytest.mark.ignore_stream('5.8')
@pytest.mark.uncollectif(lambda provider: provider.one_of(InfraProvider))  # TODO remove when common
def test_set_retirement_offset(retire_vm, warn):
    """Tests setting the retirement by offset

    Minimum is 1 hour, just testing that it is set like test_set_retirement_date
    """
    num_hours = 3
    num_days = 1
    num_weeks = 2
    num_months = 0  # leave at zero for now, TODO implement months->weeks calc for expected_dates
    retire_offset = {'months': num_months, 'weeks': num_weeks, 'days': num_days, 'hours': num_hours}
    timedelta_offset = retire_offset.copy()
    timedelta_offset.pop('months')  # for timedelta use
    # pad pre-retire timestamp by 30s
    expected_dates = {'start': datetime.utcnow() + timedelta(seconds=-30, **timedelta_offset)}
    retire_vm.set_retirement_date(offset=retire_offset, warn=warn.string)

    # pad post-retire timestamp by 30s
    expected_dates['end'] = datetime.utcnow() + timedelta(seconds=30, **timedelta_offset)
    verify_retirement_date(retire_vm,
                           expected_date=expected_dates)


@pytest.mark.rhv3
def test_unset_retirement_date(retire_vm):
    """Tests cancelling a scheduled retirement by removing the set date
    """
    num_days = 3
    retire_date = generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(retire_date)
    verify_retirement_date(retire_vm, expected_date=retire_date)

    retire_vm.set_retirement_date(None)
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
    """
    num_days = 5

    retire_vm.retire()
    verify_retirement_state(retire_vm)

    retire_date = None if remove_date else generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(retire_date)

    verify_retirement_date(retire_vm, expected_date=retire_date if retire_date else 'Never')
    assert retire_vm.is_retired is False
