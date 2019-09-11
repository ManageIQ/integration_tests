"""Global fixtures for depot tests"""
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme.utils.config_data import cfme_data
from cfme.utils.log import logger
from cfme.utils.net import find_pingable
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


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
            "long-test-depot-{}".format(fauxfactory.gen_alphanumeric()),
            template_name=data.log_db_depot_template.template_name
        )
        vm.ensure_state(VmState.RUNNING)
    except AttributeError:
        msg = 'Missing some yaml information necessary to deploy depot VM'
        logger.exception(msg)
        pytest.skip(msg)

    try:
        found_ip, _ = wait_for(
            find_pingable,
            func_args=[vm],
            fail_condition=None,
            delay=5,
            num_sec=300
        )
    except TimedOutError:
        msg = 'Timed out waiting for reachable depot VM IP'
        logger.exception(msg)
        pytest.skip(msg)

    yield found_ip
    vm.cleanup()
