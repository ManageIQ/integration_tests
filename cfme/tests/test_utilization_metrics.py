# -*- coding: utf-8 -*-

import pytest
import random
import time

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.configure.configuration import get_server_roles, set_server_roles, candu
from cfme.common.provider import BaseProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from fixtures.pytest_store import store
from fixtures.provider import setup_or_skip
from operator import attrgetter
from utils import testgen
from utils import conf
from utils.blockers import BZ
from utils.log import logger
from utils.version import current_version


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc,
        [VMwareProvider, RHEVMProvider, EC2Provider, OpenStackProvider, AzureProvider, GCEProvider],
        required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


pytestmark = [
    pytest.mark.tier(1),
    test_requirements.c_and_u
]


@pytest.yield_fixture(scope="module")
def enable_candu():
    try:
        original_roles = get_server_roles()
        new_roles = original_roles.copy()
        new_roles.update({
            'ems_metrics_coordinator': True,
            'ems_metrics_collector': True,
            'ems_metrics_processor': True,
            'automate': False,
            'smartstate': False})
        set_server_roles(**new_roles)
        candu.enable_all()
        yield
    finally:
        candu.disable_all()
        set_server_roles(**original_roles)


@pytest.yield_fixture(scope="module")
def clean_setup_provider(request, provider):
    BaseProvider.clear_providers()
    setup_or_skip(request, provider)
    yield
    BaseProvider.clear_providers()


@pytest.fixture(scope="module")
def metrics_collection(clean_setup_provider, provider, enable_candu):
    """Check the db is gathering collection data for the given provider.

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
        # Count host and vm metrics for the provider we're testing
        host_count = store.current_appliance.db.session.query(metrics_tbl).filter(
            metrics_tbl.parent_ems_id == mgmt_system_id).filter(
            metrics_tbl.resource_type == "Host"
        ).count()
        vm_count = store.current_appliance.db.session.query(metrics_tbl).filter(
            metrics_tbl.parent_ems_id == mgmt_system_id).filter(
            metrics_tbl.resource_type == "VmOrTemplate"
        ).count()

        if host_rising is not True:
            if host_count > last_host_count:
                host_rising = True
        if vm_rising is not True:
            if vm_count > last_vm_count:
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


def get_host_name(provider):
    cfme_host = random.choice(provider.data["hosts"])
    return cfme_host.name


def query_metric_db(appliance_db, provider, metric, vm_name=None, host_name=None):
    metrics_tbl = appliance_db['metrics']
    ems = appliance_db['ext_management_systems']
    if vm_name is None:
        if host_name is not None:
            object_name = host_name
    elif vm_name is not None:
        object_name = vm_name

    with appliance_db.transaction:
        provs = (
            appliance_db.session.query(metrics_tbl.id)
            .join(ems, metrics_tbl.parent_ems_id == ems.id)
            .filter(metrics_tbl.resource_name == object_name,
            ems.name == provider.name)
        )
    return appliance_db.session.query(metrics_tbl).filter(metrics_tbl.id.in_(provs.subquery()))


# Tests to check that specific metrics are being collected
@pytest.mark.uncollectif(
    lambda provider: current_version() < "5.7" and provider.type == 'gce')
def test_raw_metric_vm_cpu(metrics_collection, appliance, provider):
    vm_name = provider.data['cap_and_util']['capandu_vm']
    if provider.category == "infra":
        query = query_metric_db(appliance.db, provider, 'cpu_usagemhz_rate_average',
            vm_name)
        average_rate = attrgetter('cpu_usagemhz_rate_average')
    elif provider.category == "cloud":
        query = query_metric_db(appliance.db, provider, 'cpu_usage_rate_average',
            vm_name)
        average_rate = attrgetter('cpu_usagemhz_rate_average')

    for record in query:
        if average_rate(record) is not None:
            assert average_rate(record) > 0, 'Zero VM CPU Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.type == 'ec2' or provider.type == 'gce')
def test_raw_metric_vm_memory(metrics_collection, appliance, provider):
    vm_name = provider.data['cap_and_util']['capandu_vm']

    if provider.type == 'azure':
        query = query_metric_db(appliance.db, provider, 'mem_usage_absolute_average',
            vm_name)
        average_rate = attrgetter('mem_usage_absolute_average')
    else:
        query = query_metric_db(appliance.db, provider, 'derived_memory_used',
            vm_name)
        average_rate = attrgetter('derived_memory_used')

    for record in query:
        if average_rate(record) is not None:
            assert average_rate(record) > 0, 'Zero VM Memory Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: current_version() < "5.7" and provider.type == 'gce')
@pytest.mark.meta(
    blockers=[BZ(1408963, forced_streams=["5.6", "5.7"],
        unblock=lambda provider: provider.type != 'rhevm')]
)
def test_raw_metric_vm_network(metrics_collection, appliance, provider):
    vm_name = provider.data['cap_and_util']['capandu_vm']
    query = query_metric_db(appliance.db, provider, 'net_usage_rate_average',
        vm_name)

    for record in query:
        if record.net_usage_rate_average is not None:
            assert record.net_usage_rate_average > 0, 'Zero VM Network IO'
            break


@pytest.mark.uncollectif(
    lambda provider: current_version() < "5.7" and provider.type == 'gce')
@pytest.mark.meta(
    blockers=[BZ(1322094, forced_streams=["5.6", "5.7"],
        unblock=lambda provider: provider.type != 'rhevm')]
)
def test_raw_metric_vm_disk(metrics_collection, appliance, provider):
    vm_name = provider.data['cap_and_util']['capandu_vm']
    query = query_metric_db(appliance.db, provider, 'disk_usage_rate_average',
        vm_name)

    for record in query:
        if record.disk_usage_rate_average is not None:
            assert record.disk_usage_rate_average > 0, 'Zero VM Disk IO'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_raw_metric_host_cpu(metrics_collection, appliance, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(appliance.db, provider, 'cpu_usagemhz_rate_average',
        host_name)

    for record in query:
        if record.cpu_usagemhz_rate_average is not None:
            assert record.cpu_usagemhz_rate_average > 0, 'Zero Host CPU Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_raw_metric_host_memory(metrics_collection, appliance, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(appliance.db, provider, 'derived_memory_used',
        host_name)

    for record in query:
        if record.derived_memory_used is not None:
            assert record.derived_memory_used > 0, 'Zero Host Memory Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_raw_metric_host_network(metrics_collection, appliance, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(appliance.db, provider, 'net_usage_rate_average',
        host_name)

    for record in query:
        if record.net_usage_rate_average is not None:
            assert record.net_usage_rate_average > 0, 'Zero Host Network IO'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
@pytest.mark.meta(
    blockers=[BZ(1424589, forced_streams=["5.6", "5.7"],
        unblock=lambda provider: provider.type != 'rhevm')]
)
def test_raw_metric_host_disk(metrics_collection, appliance, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(appliance.db, provider, 'disk_usage_rate_average',
        host_name)

    for record in query:
        if record.disk_usage_rate_average is not None:
            assert record.disk_usage_rate_average > 0, 'Zero Host Disk IO'
            break
