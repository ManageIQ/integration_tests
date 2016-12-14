# -*- coding: utf-8 -*-

import pytest
import time

from cfme import test_requirements
from fixtures.pytest_store import store

from cfme.configure.configuration import server_roles_enabled, candu
from cfme.common.provider import BaseProvider
from cfme.containers.provider import ContainersProvider
from cfme.middleware.provider import MiddlewareProvider
from cfme.exceptions import FlashMessageException
from utils import providers
from utils import testgen
from utils import conf
from utils.log import logger
from utils.version import current_version


# Tests for vmware,rhev, openstack, ec2, azure, gce providers have been moved to
# cfme/tests/test_utilization_metrics.py.
# Also, this test just verifies that C&U/perf data is being collected, whereas the tests in
# test_utilization_metrics.py go a step further and verify that specific performance metrics are
# being collected.Eventually, support should be added to verify that specific metrics are being
# collected for *all* providers.
pytest_generate_tests = testgen.generate([ContainersProvider, MiddlewareProvider], scope="module")


pytestmark = [
    pytest.mark.tier(1),
    test_requirements.c_and_u
]


@pytest.yield_fixture(scope="module")
def enable_candu():
    try:
        with server_roles_enabled(
                'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor'):
            candu.enable_all()
            yield
    finally:
        candu.disable_all()


# Blow away all providers when done - collecting metrics for all of them is
# too much
@pytest.yield_fixture
def handle_provider(provider):
    try:
        BaseProvider.clear_providers()
        providers.setup_provider(provider.key)
    except FlashMessageException as e:
        e.skip_and_log("Provider failed to set up")
    else:
        yield
    finally:
        BaseProvider.clear_providers()


@pytest.mark.uncollectif(
    lambda provider: current_version() < "5.7" and provider.type == 'gce')
def test_metrics_collection(handle_provider, provider, enable_candu):
    """Check the db is gathering collection data for the given provider

    Metadata:
        test_flag: metrics_collection
    """
    metrics_tbl = store.current_appliance.db['metrics']
    mgmt_systems_tbl = store.current_appliance.db['ext_management_systems']

    logger.info("Fetching provider ID for %s", provider.key)
    mgmt_system_id = store.current_appliance.db.session.query(mgmt_systems_tbl).filter(
        mgmt_systems_tbl.name == conf.cfme_data.get('management_systems', {})[provider.key]['name']
    ).first().id

    logger.info("ID fetched; testing metrics collection now")
    start_time = time.time()
    host_count = 0
    vm_count = 0
    host_rising = False
    vm_rising = False
    timeout = 900.0  # 15 min
    while time.time() < start_time + timeout:
        last_host_count = host_count
        last_vm_count = vm_count
        logger.info("name: %s, id: %s, vms: %s, hosts: %s",
            provider.key, mgmt_system_id, vm_count, host_count)
        # count host and vm metrics for the provider we're testing
        host_count = store.current_appliance.db.session.query(metrics_tbl).filter(
            metrics_tbl.parent_ems_id == mgmt_system_id).filter(
            metrics_tbl.resource_type == "Host"
        ).count()
        vm_count = store.current_appliance.db.session.query(metrics_tbl).filter(
            metrics_tbl.parent_ems_id == mgmt_system_id).filter(
            metrics_tbl.resource_type == "VmOrTemplate"
        ).count()

        if (host_count > last_host_count) and (last_host_count > 0):
            host_rising = True
        if (vm_count > last_vm_count) and (last_vm_count > 0):
            vm_rising = True

        # only vms are collected for cloud
        if provider.category == "cloud" and vm_rising:
            return
        # both vms and hosts must be collected for infra
        elif provider.category == "infra" and vm_rising and host_rising:
            return
        else:
            time.sleep(15)

    if time.time() > start_time + timeout:
        raise Exception("Timed out waiting for metrics to be collected")
