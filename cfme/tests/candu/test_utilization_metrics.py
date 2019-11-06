# -*- coding: utf-8 -*-
import random
from operator import attrgetter

import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.provider import BaseProvider
from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import conf
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(1),
    test_requirements.c_and_u,
    pytest.mark.provider(
        [VMwareProvider, RHEVMProvider, EC2Provider, OpenStackProvider, AzureProvider],
        required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')], scope="module")
]


@pytest.fixture(scope="module")
def clean_setup_provider(request, provider):
    BaseProvider.clear_providers()
    setup_or_skip(request, provider)
    yield
    BaseProvider.clear_providers()


def vm_count(appliance, metrics_tbl, mgmt_system_id):
    return bool(appliance.db.client.session.query(metrics_tbl).filter(
        metrics_tbl.parent_ems_id == mgmt_system_id).filter(
        metrics_tbl.resource_type == "VmOrTemplate").count()
    )


def host_count(appliance, metrics_tbl, mgmt_system_id):
    return bool(appliance.db.client.session.query(metrics_tbl).filter(
        metrics_tbl.parent_ems_id == mgmt_system_id).filter(
        metrics_tbl.resource_type == "Host").count()
    )


@pytest.fixture(scope="module")
def metrics_collection(appliance, clean_setup_provider, provider, enable_candu):
    """Check the db is gathering collection data for the given provider.

    Metadata:
        test_flag: metrics_collection
    """
    metrics_tbl = appliance.db.client['metrics']
    rollups = appliance.db.client['metric_rollups']
    mgmt_systems_tbl = appliance.db.client['ext_management_systems']

    vm_name = provider.data['cap_and_util']['capandu_vm']
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(vm_name, provider)

    if not vm.exists_on_provider:
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    vm.mgmt.ensure_state(VmState.RUNNING)

    logger.info("Deleting metrics tables")
    appliance.db.client.session.query(metrics_tbl).delete()
    appliance.db.client.session.query(rollups).delete()

    logger.info("Fetching provider ID for %s", provider.key)
    mgmt_system_id = appliance.db.client.session.query(mgmt_systems_tbl).filter(
        mgmt_systems_tbl.name == conf.cfme_data.get('management_systems', {})[provider.key]['name']
    ).first().id

    logger.info("ID fetched; testing metrics collection now")

    # vms for both infa and cloud provider
    wait_for(
        vm_count, [appliance, metrics_tbl, mgmt_system_id],
        delay=20,
        timeout=1500,
        fail_condition=False,
        message="wait for VMs")

    # host only for infa
    if provider.category == "infra":
        wait_for(
            vm_count, [appliance, metrics_tbl, mgmt_system_id],
            delay=20,
            timeout=1500,
            fail_condition=False,
            message="wait for hosts.")


def get_host_name(provider):
    cfme_host = random.choice(provider.data["hosts"])
    return cfme_host.name


def query_metric_db(appliance, provider, metric, vm_name=None, host_name=None):
    metrics_tbl = appliance.db.client['metrics']
    ems = appliance.db.client['ext_management_systems']
    if vm_name is None:
        if host_name is not None:
            object_name = host_name
    elif vm_name is not None:
        object_name = vm_name

    with appliance.db.client.transaction:
        provs = (
            appliance.db.client.session.query(metrics_tbl.id)
            .join(ems, metrics_tbl.parent_ems_id == ems.id)
            .filter(metrics_tbl.resource_name == object_name,
            ems.name == provider.name)
        )
    return appliance.db.client.session.query(metrics_tbl).filter(
        metrics_tbl.id.in_(provs.subquery()))


@pytest.mark.rhv2
@pytest.mark.meta(automates=[1671580, 1722937])
# Tests to check that specific metrics are being collected
def test_raw_metric_vm_cpu(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    vm_name = provider.data['cap_and_util']['capandu_vm']
    if provider.category == "infra":
        query = query_metric_db(appliance, provider, 'cpu_usagemhz_rate_average',
            vm_name)
        average_rate = attrgetter('cpu_usagemhz_rate_average')
    elif provider.category == "cloud":
        query = query_metric_db(appliance, provider, 'cpu_usage_rate_average',
            vm_name)
        average_rate = attrgetter('cpu_usage_rate_average')

    for record in query:
        if average_rate(record) is not None:
            assert average_rate(record) > 0, 'Zero VM CPU Usage'
            break


@pytest.mark.rhv2
@pytest.mark.meta(automates=[1671580, 1722937])
@pytest.mark.meta(
    blockers=[BZ(1724415, forced_streams=['5.10', '5.11'],
        unblock=lambda provider: not provider.one_of(AzureProvider))]
)
def test_raw_metric_vm_memory(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    vm_name = provider.data['cap_and_util']['capandu_vm']

    if provider.type == 'azure':
        query = query_metric_db(appliance, provider, 'mem_usage_absolute_average',
            vm_name)
        average_rate = attrgetter('mem_usage_absolute_average')
    else:
        query = query_metric_db(appliance, provider, 'derived_memory_used',
            vm_name)
        average_rate = attrgetter('derived_memory_used')

    for record in query:
        if average_rate(record) is not None:
            assert average_rate(record) > 0, 'Zero VM Memory Usage'
            break


@pytest.mark.rhv2
@pytest.mark.meta(automates=[1671580, 1722937])
def test_raw_metric_vm_network(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/12h
        casecomponent: CandU
    """
    vm_name = provider.data['cap_and_util']['capandu_vm']
    query = query_metric_db(appliance, provider, 'net_usage_rate_average',
        vm_name)

    for record in query:
        if record.net_usage_rate_average is not None:
            assert record.net_usage_rate_average > 0, 'Zero VM Network IO'
            break


@pytest.mark.rhv2
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider, OpenStackProvider, AzureProvider, GCEProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')],
    scope='module',
    override=True
)
@pytest.mark.meta(automates=[1671580, 1722937])
def test_raw_metric_vm_disk(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/8h
        casecomponent: CandU
    """
    vm_name = provider.data['cap_and_util']['capandu_vm']
    query = query_metric_db(appliance, provider, 'disk_usage_rate_average',
        vm_name)

    for record in query:
        if record.disk_usage_rate_average is not None:
            assert record.disk_usage_rate_average > 0, 'Zero VM Disk IO'
            break


@pytest.mark.rhv2
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')],
    scope='module',
    override=True
)
def test_raw_metric_host_cpu(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    host_name = get_host_name(provider)
    query = query_metric_db(appliance, provider, 'cpu_usagemhz_rate_average',
        host_name)

    for record in query:
        if record.cpu_usagemhz_rate_average is not None:
            assert record.cpu_usagemhz_rate_average > 0, 'Zero Host CPU Usage'
            break


@pytest.mark.rhv2
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')],
    scope='module',
    override=True
)
def test_raw_metric_host_memory(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: low
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    host_name = get_host_name(provider)
    query = query_metric_db(appliance, provider, 'derived_memory_used',
        host_name)

    for record in query:
        if record.derived_memory_used is not None:
            assert record.derived_memory_used > 0, 'Zero Host Memory Usage'
            break


@pytest.mark.rhv2
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')],
    scope='module',
    override=True
)
def test_raw_metric_host_network(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/12h
        casecomponent: CandU
    """
    host_name = get_host_name(provider)
    query = query_metric_db(appliance, provider, 'net_usage_rate_average',
        host_name)

    for record in query:
        if record.net_usage_rate_average is not None:
            assert record.net_usage_rate_average > 0, 'Zero Host Network IO'
            break


@pytest.mark.rhv2
@pytest.mark.provider(
    [VMwareProvider, RHEVMProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')],
    scope='module',
    override=True
)
def test_raw_metric_host_disk(metrics_collection, appliance, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: high
        casecomponent: CandU
        initialEstimate: 1/12h
    """
    host_name = get_host_name(provider)
    query = query_metric_db(appliance, provider, 'disk_usage_rate_average',
        host_name)

    for record in query:
        if record.disk_usage_rate_average is not None:
            assert record.disk_usage_rate_average > 0, 'Zero Host Disk IO'
            break


def query_metric_rollup_table(appliance, provider, metric, azone_name):
    """
    These queries return all records pertaining to a specific Availability zone
    specified by $azone_name from the metric_rollups table.
    """
    metrics_tbl = appliance.db.client['metric_rollups']
    ems = appliance.db.client['ext_management_systems']

    with appliance.db.client.transaction:
        provs = (
            appliance.db.client.session.query(metrics_tbl.id)
            .join(ems, metrics_tbl.parent_ems_id == ems.id)
            .filter(metrics_tbl.resource_name == azone_name,
            ems.name == provider.name)
        )
    return appliance.db.client.session.query(metrics_tbl).filter(
        metrics_tbl.id.in_(provs.subquery()))


def generic_test_azone_rollup(appliance, provider, metric):
    """
    The test_azone* tests require that the metrics_collection fixture be run.
    The first metric collection is scheduled through this fixture. The first
    metric collection itself takes at least 15 minutes(sometimes longer).
    The three tests that are run per provider take at least 20 minutes each
    for completion(considering provider add, provider refresh etc.). But, without
    parametrization, the three tests could be run in under 20 minutes.So, the tests
    haven't been parametrized.

    In an effort to reduce DRY code, I've written this generic function that
    checks if any of the table records have a metric with a non-zero value.
    """
    azone_name = provider.data["cap_and_util"]["capandu_azone"]
    query = query_metric_rollup_table(appliance, provider, metric, azone_name)

    for record in query:
        if int(getattr(record, metric, 0)):
            return True
        else:
            raise ValueError('The record had a zero in it!')


@pytest.mark.provider(
    [EC2Provider, AzureProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')],
    scope="module"
)
@pytest.mark.meta(
    blockers=[BZ(1744845, forced_streams=['5.10'],
        unblock=lambda provider: not provider.one_of(AzureProvider))]
)
class TestAzone:
    def test_azone_cpu_usage(metrics_collection, appliance, provider):
        """
        Polarion:
            assignee: nachandr
            caseimportance: high
            casecomponent: CandU
            initialEstimate: 1/12h
        """
        generic_test_azone_rollup(appliance, provider, 'cpu_usage_rate_average')

    def test_azone_memory_usage(metrics_collection, appliance, provider):
        """
        Polarion:
            assignee: nachandr
            caseimportance: high
            casecomponent: CandU
            initialEstimate: 1/12h
        """
        generic_test_azone_rollup(appliance, provider, 'mem_usage_absolute_average')

    def test_azone_network_io(metrics_collection, appliance, provider):
        """
        Polarion:
            assignee: nachandr
            caseimportance: high
            casecomponent: CandU
            initialEstimate: 1/12h
        """
        generic_test_azone_rollup(appliance, provider, 'net_usage_rate_average')
