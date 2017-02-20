# -*- coding: utf-8 -*-
import pytest
from datetime import date, timedelta, datetime

from cfme import test_requirements
from cfme.common.provider import CloudInfraProvider
from cfme.common.vm import VM
from cfme.web_ui import toolbar as tb
from utils import testgen
from utils.blockers import BZ
from utils.generators import random_vm_name
from utils.log import logger
from utils.providers import ProviderFilter
from utils.timeutil import parsetime
from utils.wait import wait_for
from utils.version import pick, current_version


pytest_generate_tests = testgen.generate(
    gen_func=testgen.providers,
    filters=[ProviderFilter(classes=[CloudInfraProvider], required_flags=['provision', 'retire'])],
    scope='module')


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(2),
    pytest.mark.long_running
]


@pytest.yield_fixture(scope="function")
def test_vm(small_template, provider):
    vm = VM.factory(random_vm_name('retire'), provider, template_name=small_template)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    yield vm

    try:
        if provider.mgmt.does_vm_exist(vm.name):
            provider.mgmt.delete_vm(vm.name)
    except Exception:
        logger.warning('Failed to delete vm from provider: {}'.format(vm.name))


def verify_retirement_state(test_vm):
    # wait for the info block showing a date as retired date
    # Use lambda for is_retired since its a property
    assert wait_for(lambda: test_vm.is_retired, delay=5, num_sec=10 * 60, fail_func=tb.refresh,
             message="Wait for VM '{}' to enter retired state".format(test_vm.name))

    # TODO: remove dependency on SummaryMixin and use widgetastic when available
    assert test_vm.summary.power_management.power_state.text_value in ['off', 'suspended',
                                                                       'unknown']


def verify_retirement_date(test_vm, expected_date='Never'):
    """Verify the retirement date for a variety of situations

    Args:
        expected_date: a :py:class: `str` or :py:class: `parsetime` date
            or a dict of :py:class: `parsetime` dates with 'start' and 'end' keys.
    """
    if isinstance(expected_date, list):
        # convert to a parsetime object for comparsion, function depends on version
        if 'UTC' in pick(VM.RETIRE_DATE_FMT):
            convert_func = parsetime.from_american_minutes_with_utc
        else:
            convert_func = parsetime.from_american_date_only
        expected_date.update({'retire': convert_func(test_vm.retirement_date)})
        logger.info('Asserting retire date "%s" is between "%s" and "%s"',  # noqa
                    expected_date['retire'],
                    expected_date['start'],
                    expected_date['end'])

        assert expected_date['start'] <= expected_date['retire'] <= expected_date['end']

    elif isinstance(expected_date, (parsetime, datetime, date)):
        test_vm.retirement_date == expected_date.strftime(pick(VM.RETIRE_DATE_FMT))
    else:
        test_vm.retirement_date == expected_date


def generate_retirement_date(delta=None):
    gen_date = date.today()
    if delta:
        gen_date += timedelta(days=delta)
    return gen_date


def generate_retirement_date_now():
    return datetime.utcnow()


@test_requirements.retirement
@pytest.mark.tier(2)
def test_retirement_now(test_vm):
    """Tests on-demand retirement of an instance/vm
    """
    # For 5.7 capture two times to assert the retire time is within a window.
    # Too finicky to get it down to minute precision, nor is it really needed here
    retire_times = dict()
    retire_times['start'] = generate_retirement_date_now() + timedelta(minutes=-1)
    test_vm.retire()
    verify_retirement_state(test_vm)
    retire_times['end'] = generate_retirement_date_now() + timedelta(minutes=1)
    if current_version() < '5.7':
        verify_retirement_date(test_vm,
                               expected_date=parsetime.now().to_american_date_only())
    else:
        verify_retirement_date(test_vm, expected_date=retire_times)


@test_requirements.retirement
@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1419150, forced_streams='5.6')])
def test_set_retirement_date(test_vm):
    """Tests setting retirement date and verifies configured date is reflected in UI

    Note we cannot control the retirement time, just day, so we cannot wait for the VM to retire
    """
    num_days = 2
    retire_date = generate_retirement_date(delta=num_days)
    test_vm.set_retirement_date(retire_date, warn="1 Week before retirement")
    verify_retirement_date(test_vm, expected_date=retire_date)


@test_requirements.retirement
@pytest.mark.tier(2)
def test_unset_retirement_date(test_vm):
    """Tests cancelling a scheduled retirement by removing the set date
    """
    num_days = 3
    retire_date = generate_retirement_date(delta=num_days)
    test_vm.set_retirement_date(retire_date)
    if BZ(1419150, forced_streams='5.6').blocks:
        # The date is wrong, but we can still test unset
        logger.warning('Skipping test step verification for BZ 1419150')
    else:
        verify_retirement_date(test_vm, expected_date=retire_date)

    test_vm.set_retirement_date(None)
    verify_retirement_date(test_vm, expected_date='Never')
