# -*- coding: utf-8 -*-

""" Tests to validate chargeback costs for resources(memory, cpu, storage) allocated to VMs.

The tests to validate resource usage are in :
cfme/tests/intelligence/reports/test_validate_chargeback_report.py

Note: When the tests were parameterized, it was observed that the fixture scope was not preserved in
parametrized tests.This is supposed to be a known pytest bug.

This test module has a few module scoped fixtures that actually get invoked for every parameterized
test, despite the fact that these fixtures are module scoped.So, the tests have not been
parameterized.
"""
import math
from datetime import timedelta

import fauxfactory
import pytest

import cfme.intelligence.chargeback.assignments as cb
import cfme.intelligence.chargeback.rates as rates
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.meta(blockers=[BZ(1511099, forced_streams=['5.9', '5.8'],
                                  unblock=lambda provider: not provider.one_of(GCEProvider)),
                               ]),
    pytest.mark.provider([SCVMMProvider], scope='module',
                        required_fields=[(['cap_and_util', 'test_chargeback'], True)]),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.chargeback,
]

# Allowed deviation between the reported value in the Chargeback report and the estimated value.
DEVIATION = 1


@pytest.yield_fixture(scope="module")
def vm_ownership(enable_candu, provider, appliance):
    """In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    assigned ownership.
    """
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    if not provider.mgmt.does_vm_exist(vm_name):
        pytest.skip('Skipping test, {} VM does not exist'.format(vm_name))
    if not provider.mgmt.is_vm_running(vm_name):
        provider.mgmt.start_vm(vm_name)
        provider.mgmt.wait_vm_running(vm_name)

    group_collection = appliance.collections.groups
    cb_group = group_collection.instantiate(description='EvmGroup-user')

    vm = VM.factory(vm_name, provider)
    user = appliance.collections.users.create(
        name="{}_{}".format(provider.name, fauxfactory.gen_alphanumeric()),
        credential=Credential(principal='uid{}'.format(fauxfactory.gen_alphanumeric()),
            secret='secret'),
        email='abc@example.com',
        groups=cb_group,
        cost_center='Workload',
        value_assign='Database')
    vm.set_ownership(user=user.name)
    logger.info('Assigned VM OWNERSHIP for {} running on {}'.format(vm_name, provider.name))
    yield user.name

    vm.unset_ownership()
    if user:
        user.delete()


@pytest.yield_fixture(scope="module")
def enable_candu(provider, appliance):
    """C&U data collection consumes a lot of memory and CPU.So, we are disabling some server roles
    that are not needed for Chargeback reporting.
    """
    candu = appliance.collections.candus
    server_info = appliance.server.settings
    original_roles = server_info.server_roles_db
    server_info.enable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    server_info.disable_server_roles('automate', 'smartstate')
    candu.enable_all()
    yield

    server_info.update_server_roles_db(original_roles)
    candu.disable_all()


@pytest.yield_fixture(scope="module")
def assign_custom_rate(new_chargeback_rate, provider):
    """Assign custom Compute rate to the Enterprise and then queue the Chargeback report."""
    description = new_chargeback_rate
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': description}
        })
    enterprise.computeassign()
    enterprise.storageassign()
    logger.info('Assigning CUSTOM Compute rate')
    yield

    # Resetting the Chargeback rate assignment
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': '<Nothing>'}
        })
    enterprise.computeassign()
    enterprise.storageassign()


def verify_vm_uptime(appliance, provider):
    """Verify VM uptime is at least one hour.That is the shortest duration for
    which VMs can be charged.
    """
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    vm_creation_time = appliance.rest_api.collections.vms.get(name=vm_name).created_on
    return appliance.utc_time() - vm_creation_time > timedelta(hours=1)


@pytest.fixture(scope="module")
def resource_alloc(vm_ownership, appliance, provider):
    """Retrieve resource allocation values"""
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    if provider.one_of(SCVMMProvider):
        wait_for(verify_vm_uptime, [appliance, provider], timeout=3610,
            message='Waiting for VM to be up for at least one hour')

    vm = appliance.rest_api.collections.vms.get(name=vm_name)
    vm.reload(attributes=['allocated_disk_storage', 'cpu_total_cores', 'ram_size'])

    # By default,chargeback rates for storage are defined in this form: 0.01 USD/GB
    # Hence,convert storage used in Bytes to GB
    return {"storage_alloc": float(vm.allocated_disk_storage) * math.pow(2, -30),
            "memory_alloc": vm.ram_size,
            "vcpu_alloc": vm.cpu_total_cores}


def resource_cost(appliance, provider, metric_description, usage, description, rate_type):
    """Query the DB for Chargeback rates"""
    tiers = appliance.db.client['chargeback_tiers']
    details = appliance.db.client['chargeback_rate_details']
    cb_rates = appliance.db.client['chargeback_rates']
    list_of_rates = []

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(tiers).
            join(details, tiers.chargeback_rate_detail_id == details.id).
            join(cb_rates, details.chargeback_rate_id == cb_rates.id).
            filter(details.description == metric_description).
            filter(cb_rates.rate_type == rate_type).
            filter(cb_rates.description == description).all()
        )
    for row in result:
        tiered_rate = {var: getattr(row, var) for var in ['variable_rate', 'fixed_rate', 'start',
            'finish']}
        list_of_rates.append(tiered_rate)

    # Check what tier the usage belongs to and then compute the usage cost based on Fixed and
    # Variable Chargeback rates.
    for d in list_of_rates:
        if usage >= d['start'] and usage < d['finish']:
            cost = d['variable_rate'] * usage + d['fixed_rate']
            return cost


@pytest.fixture(scope="module")
def chargeback_costs_custom(resource_alloc, new_chargeback_rate, appliance, provider):
    """Estimate Chargeback costs using custom Chargeback rate and resource allocation"""
    description = new_chargeback_rate
    storage_alloc = resource_alloc['storage_alloc']
    memory_alloc = resource_alloc['memory_alloc']
    vcpu_alloc = resource_alloc['vcpu_alloc']

    storage_alloc_cost = resource_cost(appliance, provider, 'Allocated Disk Storage',
        storage_alloc, description, 'Storage')

    memory_alloc_cost = resource_cost(appliance, provider, 'Allocated Memory',
        memory_alloc, description, 'Compute')

    vcpu_alloc_cost = resource_cost(appliance, provider, 'Allocated CPU Count',
        vcpu_alloc, description, 'Compute')

    return {"storage_alloc_cost": storage_alloc_cost,
            "memory_alloc_cost": memory_alloc_cost,
            "vcpu_alloc_cost": vcpu_alloc_cost}


@pytest.yield_fixture(scope="module")
def chargeback_report_custom(appliance, vm_ownership, assign_custom_rate, provider):
    """Create a Chargeback report based on a custom rate; Queue the report"""
    owner = vm_ownership
    data = {
        'menu_name': '{}_{}'.format(provider.name, fauxfactory.gen_alphanumeric()),
        'title': '{}_{}'.format(provider.name, fauxfactory.gen_alphanumeric()),
        'base_report_on': 'Chargeback for Vms',
        'report_fields': ['Memory Allocated Cost', 'Memory Allocated over Time Period', 'Owner',
        'vCPUs Allocated over Time Period', 'vCPUs Allocated Cost',
        'Storage Allocated', 'Storage Allocated Cost'],
        'filter': {
            'filter_show_costs': 'Owner',
            'filter_owner': owner,
            'interval_end': 'Today (partial)'
        }
    }
    report = appliance.collections.reports.create(is_candu=True, **data)

    logger.info('Queuing chargeback report with custom rate for {} provider'.format(provider.name))
    report.queue(wait_for_finish=True)

    if not list(report.saved_reports.all()[0].data.rows):
        pytest.skip('Empty report')
    else:
        yield list(report.saved_reports.all()[0].data.rows)

    if report.exists:
        report.delete()


@pytest.yield_fixture(scope="module")
def new_chargeback_rate():
    """Create a new chargeback rate"""
    desc = 'custom_{}'.format(fauxfactory.gen_alphanumeric())
    compute = rates.ComputeRate(description=desc,
        fields={'Allocated CPU Count':
                {'per_time': 'Hourly', 'variable_rate': '2'},
                'Allocated Memory':
                {'per_time': 'Hourly', 'variable_rate': '2'}}
    )
    compute.create()
    if not BZ(1532368, forced_streams=['5.9']).blocks:
        storage = rates.StorageRate(description=desc,
            fields={'Allocated Disk Storage':
                    {'per_time': 'Hourly', 'variable_rate': '3'}}
        )
    storage.create()
    yield desc

    if compute.exists:
        compute.delete()
    if not BZ(1532368, forced_streams=['5.9']).blocks and storage.exists:
        storage.delete()


def generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom, column,
        resource_alloc_cost, soft_assert):
    """Generic test to validate resource allocation cost reported in chargeback reports.

    Steps:
        1.Create chargeback report for VMs.Include fields for resource allocation
          and resource allocation costs in the report.
        2.Fetch chargeback rates from DB and calculate cost estimates for allocated resources
        3.Validate the costs reported in the chargeback report.The costs in the report should
          be approximately equal to the cost estimated in the resource_cost fixture.
    """
    for groups in chargeback_report_custom:
        if not groups[column]:
            pytest.skip('missing column in report')
        else:
            estimated_resource_alloc_cost = chargeback_costs_custom[resource_alloc_cost]
            cost_from_report = groups[column]
            cost = cost_from_report.replace('$', '').replace(',', '')
            soft_assert(estimated_resource_alloc_cost - DEVIATION <=
                float(cost) <= estimated_resource_alloc_cost + DEVIATION,
                'Estimated cost and report cost do not match')


def generic_test_resource_alloc(resource_alloc, chargeback_report_custom, column,
        resource, soft_assert):
    """Generic test to verify VM resource allocation reported in chargeback reports.

    Steps:
        1.Create chargeback report for VMs.Include fields for resource allocation
          and resource allocation costs in the report.
        2.Fetch resource allocation values using REST API.
        3.Verify that the resource allocation values reported in the chargeback report
          match the values fetched through REST API.
    """
    for groups in chargeback_report_custom:
        if not groups[column]:
            pytest.skip('missing column in report')
        else:
            allocated_resource = resource_alloc[resource]
            if 'GB' in groups[column] and column == 'Memory Allocated over Time Period':
                allocated_resource = float(allocated_resource) * math.pow(2, -10)
            resource_from_report = groups[column].replace('MB', '').replace('GB', '')
            soft_assert(allocated_resource - DEVIATION <=
                float(resource_from_report) <= allocated_resource + DEVIATION,
                'Estimated resource allocation and report resource allocation do not match')


def test_verify_alloc_memory(resource_alloc, chargeback_report_custom, soft_assert):
    """Test to verify memory allocation"""
    generic_test_resource_alloc(resource_alloc, chargeback_report_custom,
        'Memory Allocated over Time Period', 'memory_alloc', soft_assert)


def test_verify_alloc_cpu(resource_alloc, chargeback_report_custom, soft_assert):
    """Test to verify cpu allocation"""
    generic_test_resource_alloc(resource_alloc, chargeback_report_custom,
        'vCPUs Allocated over Time Period', 'vcpu_alloc', soft_assert)


def test_verify_alloc_storage(resource_alloc, chargeback_report_custom, soft_assert):
    """Test to verify storage allocation"""
    generic_test_resource_alloc(resource_alloc, chargeback_report_custom,
        'Storage Allocated', 'storage_alloc', soft_assert)


def test_validate_alloc_memory_cost(chargeback_costs_custom, chargeback_report_custom,
        soft_assert):
    """Test to validate cost for memory allocation"""
    generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom,
        'Memory Allocated Cost', 'memory_alloc_cost', soft_assert)


def test_validate_alloc_vcpu_cost(chargeback_costs_custom, chargeback_report_custom,
        soft_assert):
    """Test to validate cost for vCPU allocation"""
    generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom,
        'vCPUs Allocated Cost', 'vcpu_alloc_cost', soft_assert)


def test_validate_alloc_storage_cost(chargeback_costs_custom, chargeback_report_custom,
        soft_assert):
    """Test to validate cost for storage allocation"""
    generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom,
        'Storage Allocated Cost', 'storage_alloc_cost', soft_assert)
