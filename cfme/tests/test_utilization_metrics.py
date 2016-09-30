# -*- coding: utf-8 -*-

import pytest
import random
import time

from cfme import test_requirements
from fixtures.pytest_store import store
from utils import providers
from utils import testgen
from utils import conf
from utils.blockers import BZ
from utils.log import logger
from cfme.configure.configuration import get_server_roles, set_server_roles, candu
from cfme.common.provider import BaseProvider
from cfme.exceptions import FlashMessageException


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc, ['virtualcenter', 'rhevm',
        'ec2', 'rhos'])
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


# Blow away all providers when done - collecting metrics for all of them is
# too much
@pytest.yield_fixture(scope="module")
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


@pytest.fixture(scope="module")
def metrics_collection(handle_provider, provider, enable_candu):
    """check the db is gathering collection data for the given provider

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


def get_host_name(provider):
    cfme_host = random.choice(provider.data["hosts"])
    return cfme_host.name


def query_metric_db(db, provider, metric, vm_name=None, host_name=None):
    metrics_tbl = db['metrics']
    ems = db['ext_management_systems']
    if vm_name is None:
        if host_name is not None:
            object_name = host_name
    elif vm_name is not None:
        object_name = vm_name

    with db.transaction:
        provs = (
            db.session.query(metrics_tbl.id)
            .join(ems, metrics_tbl.parent_ems_id == ems.id)
            .filter(metrics_tbl.resource_name == object_name,
            ems.name == provider.name)
        )
    return db.session.query(metrics_tbl).filter(metrics_tbl.id.in_(provs.subquery()))


# Tests to check that specific metrics are being collected
def test_raw_metric_vm_cpu(metrics_collection, db, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    if provider.category == "infra":
        query = query_metric_db(db, provider, 'cpu_usagemhz_rate_average',
            vm_name)
    elif provider.category == "cloud":
        query = query_metric_db(db, provider, 'cpu_usage_rate_average',
            vm_name)

    for record in query:
        if record.cpu_usagemhz_rate_average is None:
            pass
        else:
            assert record.cpu_usagemhz_rate_average > 0, 'Zero VM CPU Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.type == 'ec2')
def test_raw_metric_vm_memory(metrics_collection, db, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    query = query_metric_db(db, provider, 'derived_memory_used',
        vm_name)

    for record in query:
        if record.derived_memory_used is None:
            pass
        else:
            assert record.derived_memory_used > 0, 'Zero VM Memory usage'
            break


@pytest.mark.meta(
    blockers=[BZ(1322094, unblock=lambda provider: provider.type != 'rhevm')]
)
def test_raw_metric_vm_network(metrics_collection, db, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    query = query_metric_db(db, provider, 'net_usage_rate_average',
        vm_name)

    for record in query:
        if record.net_usage_rate_average is None:
            pass
        else:
            assert record.net_usage_rate_average > 0, 'Zero VM Network IO'
            break


@pytest.mark.meta(
    blockers=[BZ(1322094, unblock=lambda provider: provider.type != 'rhevm')]
)
def test_raw_metric_vm_disk(metrics_collection, db, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    query = query_metric_db(db, provider, 'disk_usage_rate_average',
        vm_name)

    for record in query:
        if record.disk_usage_rate_average is None:
            pass
        else:
            assert record.disk_usage_rate_average > 0, 'Zero VM Disk IO'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_raw_metric_host_cpu(metrics_collection, db, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(db, provider, 'cpu_usagemhz_rate_average',
        host_name)

    for record in query:
        if record.cpu_usagemhz_rate_average is None:
            pass
        else:
            assert record.cpu_usagemhz_rate_average > 0, 'Zero Host CPU Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_raw_metric_host_memory(metrics_collection, db, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(db, provider, 'derived_memory_used',
        host_name)

    for record in query:
        if record.derived_memory_used is None:
            pass
        else:
            assert record.derived_memory_used > 0, 'Zero Host Memory Usage'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_raw_metric_host_network(metrics_collection, db, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(db, provider, 'net_usage_rate_average',
        host_name)

    for record in query:
        if record.net_usage_rate_average is None:
            pass
        else:
            assert record.net_usage_rate_average > 0, 'Zero Host Network IO'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
@pytest.mark.meta(
    blockers=[BZ(1322094, unblock=lambda provider: provider.type != 'rhevm')]
)
def test_raw_metric_host_disk(metrics_collection, db, provider):
    host_name = get_host_name(provider)
    query = query_metric_db(db, provider, 'disk_usage_rate_average',
        host_name)

    for record in query:
        if record.disk_usage_rate_average is None:
            pass
        else:
            assert record.disk_usage_rate_average > 0, 'Zero Host Disk IO'
            break
