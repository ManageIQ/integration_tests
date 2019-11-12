import time

import pytest

from cfme import test_requirements
from cfme.common.provider import BaseProvider
from cfme.containers.provider import ContainersProvider
from cfme.fixtures.provider import setup_or_skip
from cfme.fixtures.pytest_store import store
from cfme.utils import conf
from cfme.utils.log import logger


# Tests for vmware,rhev, openstack, ec2, azure, gce providers have been moved to
# cfme/tests/test_utilization_metrics.py.
# Also, this test just verifies that C&U/perf data is being collected, whereas the tests in
# test_utilization_metrics.py go a step further and verify that specific performance metrics are
# being collected.Eventually, support should be added to verify that specific metrics are being
# collected for *all* providers.


pytestmark = [
    pytest.mark.tier(1),
    test_requirements.c_and_u,
    pytest.mark.provider([ContainersProvider], scope="module")
]


@pytest.fixture(scope="module")
def enable_candu(appliance):
    candu = appliance.collections.candus
    original_roles = appliance.server.settings.server_roles_db
    try:
        appliance.server.settings.enable_server_roles(
            'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
        candu.enable_all()
        yield
    finally:
        candu.disable_all()
        appliance.server.settings.update_server_roles_db(original_roles)


# Blow away all providers when done - collecting metrics for all of them is too much
@pytest.fixture(scope="module")
def clean_setup_provider(request, provider):
    BaseProvider.clear_providers()
    setup_or_skip(request, provider)
    yield
    BaseProvider.clear_providers()


def test_metrics_collection(clean_setup_provider, provider, enable_candu):
    """Check the db is gathering collection data for the given provider

    Metadata:
        test_flag: metrics_collection

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    metrics_tbl = store.current_appliance.db.client['metrics']
    mgmt_systems_tbl = store.current_appliance.db.client['ext_management_systems']

    logger.info("Fetching provider ID for %s", provider.key)
    mgmt_system_id = store.current_appliance.db.client.session.query(mgmt_systems_tbl).filter(
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
        host_count = store.current_appliance.db.client.session.query(metrics_tbl).filter(
            metrics_tbl.parent_ems_id == mgmt_system_id).filter(
            metrics_tbl.resource_type == "Host"
        ).count()
        vm_count = store.current_appliance.db.client.session.query(metrics_tbl).filter(
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
