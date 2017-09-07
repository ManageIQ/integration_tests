# -*- coding: utf-8 -*-
import pytest
from collections import namedtuple
from datetime import date, timedelta, datetime

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.common.provider import CloudInfraProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.web_ui import toolbar as tb
from cfme.utils import testgen
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.timeutil import parsetime
from cfme.utils.wait import wait_for
from cfme.utils.version import pick, current_version


pytest_generate_tests = testgen.generate(
    gen_func=testgen.providers,
    filters=[ProviderFilter(classes=[CloudInfraProvider], required_flags=['provision', 'retire'])])


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.long_running
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
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    yield vm

    try:
        if provider.mgmt.does_vm_exist(vm.name):
            provider.mgmt.delete_vm(vm.name)
    except Exception:
        logger.warning('Failed to delete vm from provider: {}'.format(vm.name))


@pytest.yield_fixture(scope="function")
def retire_ec2_s3_vm(provider):
    """Fixture for creating an S3 backed paravirtual instance, template is a public ec2 AMI

    Args:
        provider: provider crud object from fixture
    """
    vm = VM.factory(random_vm_name('retire'), provider,
                    template_name='amzn-ami-pv-2015.03.rc-1.x86_64-s3')
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    yield vm

    try:
        if provider.mgmt.does_vm_exist(vm.name):
            provider.mgmt.delete_vm(vm.name)
    except Exception:
        logger.warning('Failed to delete vm from provider: {}'.format(vm.name))


def verify_retirement_state(retire_vm):
    """Verify the vm/instance is in the 'retired' state in the UI and assert its power state

    Args:
        retire_vm: vm/instance object
    """
    # wait for the info block showing a date as retired date
    # Use lambda for is_retired since its a property
    assert wait_for(lambda: retire_vm.is_retired, delay=5, num_sec=10 * 60, fail_func=tb.refresh,
             message="Wait for VM '{}' to enter retired state".format(retire_vm.name))

    retirement_states = ['off', 'suspended', 'unknown', 'terminated']
    # TODO: remove dependency on SummaryMixin and use widgetastic when available
    assert retire_vm.summary.power_management.power_state.text_value in retirement_states


def verify_retirement_date(retire_vm, expected_date='Never'):
    """Verify the retirement date for a variety of situations

    Args:
        expected_date: a :py:class: `str` or :py:class: `parsetime` date
            or a dict of :py:class: `parsetime` dates with 'start' and 'end' keys.
    """
    if isinstance(expected_date, dict):
        # convert to a parsetime object for comparsion, function depends on version
        if 'UTC' in pick(VM.RETIRE_DATE_FMT):
            convert_func = parsetime.from_american_minutes_with_utc
        else:
            convert_func = parsetime.from_american_date_only
        expected_date.update({'retire': convert_func(retire_vm.retirement_date)})
        logger.info('Asserting retire date "%s" is between "%s" and "%s"',  # noqa
                    expected_date['retire'],
                    expected_date['start'],
                    expected_date['end'])

        assert expected_date['start'] <= expected_date['retire'] <= expected_date['end']

    elif isinstance(expected_date, (parsetime, datetime, date)):
        assert retire_vm.retirement_date == expected_date.strftime(pick(VM.RETIRE_DATE_FMT))
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


@test_requirements.retirement
@pytest.mark.tier(1)
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


@test_requirements.retirement
@pytest.mark.tier(1)
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
    assert wait_for(lambda: retire_ec2_s3_vm.is_retired,
                    delay=5, num_sec=10 * 60, fail_func=tb.refresh,
                    message="Wait for VM '{}' to enter retired state"
                    .format(retire_ec2_s3_vm.name))
    assert retire_ec2_s3_vm.summary.power_management.power_state.text_value in expected_power_state
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=5)
    verify_retirement_date(retire_ec2_s3_vm, expected_date=retire_times)


@test_requirements.retirement
@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1419150, forced_streams='5.6',
                               unblock=lambda: current_version() >= '5.7')])
@pytest.mark.parametrize('warn', warnings, ids=[warning.id for warning in warnings])
def test_set_retirement_date(retire_vm, warn):
    """Tests setting retirement date and verifies configured date is reflected in UI

    Note we cannot control the retirement time, just day, so we cannot wait for the VM to retire
    """
    num_days = 2
    retire_date = generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(retire_date, warn=warn.string)
    verify_retirement_date(retire_vm, expected_date=retire_date)


@test_requirements.retirement
@pytest.mark.tier(1)
def test_unset_retirement_date(retire_vm):
    """Tests cancelling a scheduled retirement by removing the set date
    """
    num_days = 3
    retire_date = generate_retirement_date(delta=num_days)
    retire_vm.set_retirement_date(retire_date)
    if BZ(1419150, forced_streams=['5.6']).blocks:
        # The date is wrong, but we can still test unset
        logger.warning('Skipping test step verification for BZ 1419150')
    else:
        verify_retirement_date(retire_vm, expected_date=retire_date)

    retire_vm.set_retirement_date(None)
    verify_retirement_date(retire_vm, expected_date='Never')


@test_requirements.retirement
@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1306471, unblock=lambda provider: provider.one_of(InfraProvider)),
                            BZ(1430373, forced_streams=['5.6'],
                               unblock=lambda provider: provider.one_of(InfraProvider))])
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

    if BZ(1419150, forced_streams=['5.6']).blocks and not remove_date:
        # The date is wrong in 5.6, but we can still test unset
        logger.warning('Skipping test step verification for BZ 1419150')
    else:
        verify_retirement_date(retire_vm, expected_date=retire_date if retire_date else 'Never')
    assert retire_vm.is_retired is False
