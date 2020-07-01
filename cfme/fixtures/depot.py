"""Global fixtures for depot tests"""
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.net import find_pingable
from cfme.utils.net import find_pingable_ipv6
from cfme.utils.net import pick_responding_ip
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

FTP_PORT = 21


@pytest.fixture(scope="module")
def depot_machine_ip(request, appliance):
    """ Deploy vm for depot test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    try:
        # use long-test name so it has a longer life before automatic cleanup
        data = cfme_data.log_db_operations
        vm = deploy_template(
            data.log_db_depot_template.provider,
            fauxfactory.gen_alphanumeric(26, start="long-test-depot-"),
            template_name=data.log_db_depot_template.template_name
        )
        vm.ensure_state(VmState.RUNNING)
    except AttributeError:
        msg = 'Missing some yaml information necessary to deploy depot VM'
        logger.exception(msg)
        pytest.skip(msg)

    try:
        # TODO It would be better to use retry_connect here, but this requires changes to other
        #  fixtures.
        found_ip = pick_responding_ip(lambda: vm.all_ips, FTP_PORT, 300, 5, 10)
    except TimedOutError:
        msg = 'Timed out waiting for reachable depot VM IP'
        logger.exception(msg)
        pytest.skip(msg)

    yield found_ip
    vm.cleanup()


@pytest.fixture(scope="module")
def depot_machine_ipv4_and_ipv6(request, appliance):
    """ Deploy vm for depot test

    This fixture is used for deploying a vm on a provider from the yamls and getting its ip
    (both ipv4 and ipv6)
    After test run vm deletes from provider
    """
    try:
        # use long-test name so it has a longer life before automatic cleanup
        data = cfme_data.log_db_operations
        vm = deploy_template(
            data.log_db_depot_template.provider,
            f"long-test-depot-{fauxfactory.gen_alphanumeric()}",
            template_name=data.log_db_depot_template.template_name
        )
        vm.ensure_state(VmState.RUNNING)
    except AttributeError:
        msg = 'Missing some yaml information necessary to deploy depot VM'
        logger.exception(msg)
        pytest.skip(msg)

    try:
        ipv4, _ = wait_for(
            find_pingable,
            func_args=[vm, False],
            fail_condition=None,
            delay=5,
            num_sec=300
        )
        ipv6, _ = wait_for(
            find_pingable_ipv6,
            func_args=[vm],
            fail_condition=None,
            delay=5,
            num_sec=300
        )
    except TimedOutError:
        msg = 'Timed out waiting for reachable depot VM IP'
        logger.exception(msg)
        pytest.skip(msg)

    yield ipv4, ipv6
    vm.cleanup()
