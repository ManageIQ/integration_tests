"""Chargeback reports are supported for all infra and cloud providers.

Chargeback reports report costs based on 1)resource usage, 2)resource allocation
Costs are reported for the usage of the following resources by VMs:
memory, cpu, network io, disk io, storage.
Costs are reported for the allocation of the following resources to VMs:
memory, cpu, storage

So, for a provider such as VMware that supports C&U, a chargeback report would show costs for both
resource usage and resource allocation.

But, for a provider such as SCVMM that doesn't support C&U,chargeback reports show costs for
resource allocation only.

The tests in this module validate costs for resources(memory, cpu, storage) allocated to VMs.

The tests to validate resource usage are in :
cfme/tests/intelligence/reports/test_validate_chargeback_report.py

Note: When the tests were parameterized, it was observed that the fixture scope was not preserved in
parametrized tests.This is supposed to be a known pytest bug.

This test module has a few module scoped fixtures that actually get invoked for every parameterized
test, despite the fact that these fixtures are module scoped.So, the tests have not been
parameterized.
"""
import math
from datetime import date
from datetime import timedelta

import fauxfactory
import pytest
from wrapanapi import VmState

import cfme.intelligence.chargeback.assignments as cb
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.long_running,
    pytest.mark.provider([CloudProvider, InfraProvider], scope='module', selector=ONE_PER_TYPE,
                         required_fields=[(['cap_and_util', 'test_chargeback'], True)]),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
]

# Allowed deviation between the reported value in the Chargeback report and the estimated value.
# COST_DEVIATION is the allowed deviation for the chargeback cost for the allocated resource.
# RESOURCE_ALLOC_DEVIATION is the allowed deviation for the allocated resource itself.
COST_DEVIATION = 1
RESOURCE_ALLOC_DEVIATION = 0.25


@pytest.yield_fixture(scope="module")
def vm_ownership(enable_candu, provider, appliance):
    """In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    assigned ownership.
    """
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    vm = appliance.provider_based_collection(provider, coll_type='vms').instantiate(vm_name,
                                                                                    provider)
    if not vm.exists_on_provider:
        pytest.skip(f'Skipping test, {vm_name} VM does not exist')
    vm.mgmt.ensure_state(VmState.RUNNING)

    group_collection = appliance.collections.groups
    cb_group = group_collection.instantiate(description='EvmGroup-user')
    user = appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric(25, start=provider.name),
        credential=Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
                              secret='secret'),
        email='abc@example.com',
        groups=cb_group,
        cost_center='Workload',
        value_assign='Database')
    vm.set_ownership(user=user)
    logger.info(f'Assigned VM OWNERSHIP for {vm_name} running on {provider.name}')
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
    # TODO Move this to a global fixture
    for klass in (cb.ComputeAssign, cb.StorageAssign):
        enterprise = klass(
            assign_to="The Enterprise",
            selections={
                'Enterprise': {'Rate': description}
            })
        enterprise.assign()
    logger.info('Assigning CUSTOM Compute rate')
    yield

    # Resetting the Chargeback rate assignment
    for klass in (cb.ComputeAssign, cb.StorageAssign):
        enterprise = klass(
            assign_to="The Enterprise",
            selections={
                'Enterprise': {'Rate': '<Nothing>'}
            })
        enterprise.assign()


def verify_vm_uptime(appliance, provider):
    """Verify VM uptime is at least one hour.That is the shortest duration for
    which VMs can be charged.
    """
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    vm_creation_time = appliance.rest_api.collections.vms.get(name=vm_name).created_on
    return appliance.utc_time() - vm_creation_time > timedelta(hours=1)


def verify_records_rollups_table(appliance, provider):
    """ Verify that hourly rollups are present in the metric_rollups table """
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    ems = appliance.db.client['ext_management_systems']
    rollups = appliance.db.client['metric_rollups']

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(rollups.capture_interval_name == 'hourly', rollups.resource_name == vm_name,
            ems.name == provider.name, rollups.timestamp >= date.today())
        )

    for record in appliance.db.client.session.query(rollups).filter(
            rollups.id.in_(result.subquery())):
        return any([record.cpu_usagemhz_rate_average,
           record.cpu_usage_rate_average,
           record.derived_memory_used,
           record.net_usage_rate_average,
           record.disk_usage_rate_average])
    return False


def verify_records_metrics_table(appliance, provider):
    """Verify that rollups are present in the metric_rollups table"""
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    ems = appliance.db.client['ext_management_systems']
    metrics = appliance.db.client['metrics']

    # Capture real-time C&U data
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_capture('realtime', 1.hour.ago.utc, Time.now.utc)\""
        .format(provider.id, repr(vm_name)))
    assert ret.success, f"Failed to capture VM C&U data:"

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(metrics.id)
            .join(ems, metrics.parent_ems_id == ems.id)
            .filter(metrics.capture_interval_name == 'realtime',
            metrics.resource_name == vm_name,
            ems.name == provider.name, metrics.timestamp >= date.today())
        )

    for record in appliance.db.client.session.query(metrics).filter(
            metrics.id.in_(result.subquery())):
        return any([record.cpu_usagemhz_rate_average,
            record.cpu_usage_rate_average,
            record.derived_memory_used,
            record.net_usage_rate_average,
            record.disk_usage_rate_average])
    return False


@pytest.fixture(scope="module")
def resource_alloc(vm_ownership, appliance, provider):
    """Retrieve resource allocation values

    Since SCVMM doesn't support C&U,the resource allocation values are fetched from
    form Vm which is represented by rails model
    ManageIQ::Providers::Microsoft::InfraManager::Vm .

    For all other providers that support C&U, the resource allocation values are fetched
    from the DB.
    """
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    if provider.one_of(SCVMMProvider):
        wait_for(verify_vm_uptime, [appliance, provider], timeout=3610,
           message='Waiting for VM to be up for at least one hour')

        vm = appliance.rest_api.collections.vms.get(name=vm_name)
        vm.reload(attributes=['allocated_disk_storage', 'cpu_total_cores', 'ram_size'])
        # By default,chargeback rates for storage are defined in this form: 0.01 USD/GB
        # Hence,convert storage used in Bytes to GB
        return {"storage_alloc": float(vm.allocated_disk_storage) * math.pow(2, -30),
                "memory_alloc": float(vm.ram_size),
                "vcpu_alloc": float(vm.cpu_total_cores)}

    metrics = appliance.db.client['metrics']
    rollups = appliance.db.client['metric_rollups']
    ems = appliance.db.client['ext_management_systems']
    logger.info('Deleting METRICS DATA from metrics and metric_rollups tables')

    appliance.db.client.session.query(metrics).delete()
    appliance.db.client.session.query(rollups).delete()

    wait_for(verify_records_metrics_table, [appliance, provider], timeout=600,
        message='Waiting for VM real-time data')

    # New C&U data may sneak in since 1)C&U server roles are running and 2)collection for clusters
    # and hosts is on.This would mess up our Chargeback calculations, so we are disabling C&U
    # collection after data has been fetched for the last hour.

    appliance.server.settings.disable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector')

    # Perform rollup of C&U data.
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_rollup_range(1.hour.ago.utc, Time.now.utc,'realtime')\"".
        format(provider.id, repr(vm_name)))
    assert ret.success, f"Failed to rollup VM C&U data:"

    wait_for(verify_records_rollups_table, [appliance, provider], timeout=600,
        message='Waiting for hourly rollups')

    # Since we are collecting C&U data for > 1 hour, there will be multiple hourly records per VM
    # in the metric_rollups DB table.The values from these hourly records are summed up.

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(metrics.id)
            .join(ems, metrics.parent_ems_id == ems.id)
            .filter(metrics.capture_interval_name == 'realtime', metrics.resource_name == vm_name,
            ems.name == provider.name, metrics.timestamp >= date.today())
        )
    for record in appliance.db.client.session.query(metrics).filter(
            metrics.id.in_(result.subquery())):
        if all([record.derived_vm_numvcpus, record.derived_memory_available,
                record.derived_vm_allocated_disk_storage]):
            break

    # By default,chargeback rates for storage are defined in this form: 0.01 USD/GB
    # Hence,convert storage used in Bytes to GB

    return {"vcpu_alloc": float(record.derived_vm_numvcpus),
            "memory_alloc": float(record.derived_memory_available),
            "storage_alloc": float(record.derived_vm_allocated_disk_storage * math.pow(2, -30))}


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

    logger.info(f'Queuing chargeback report with custom rate for {provider.name} provider')
    report.queue(wait_for_finish=True)

    if not list(report.saved_reports.all()[0].data.rows):
        pytest.skip('Empty report')
    else:
        yield list(report.saved_reports.all()[0].data.rows)

    if report.exists:
        report.delete()


@pytest.yield_fixture(scope="module")
def new_chargeback_rate(appliance):
    """Create a new chargeback rate"""
    desc = fauxfactory.gen_alphanumeric(15, start="custom_")
    try:
        compute = appliance.collections.compute_rates.create(
            description=desc,
            fields={
                'Allocated CPU Count': {'per_time': 'Hourly', 'variable_rate': '2'},
                'Allocated Memory': {'per_time': 'Hourly', 'variable_rate': '2'}
            }
        )
        storage = appliance.collections.storage_rates.create(
            description=desc,
            fields={
                'Allocated Disk Storage': {'per_time': 'Hourly', 'variable_rate': '3'}
            }
        )
    except Exception as ex:
        pytest.fail(
            'Exception while creating compute/storage rates for chargeback allocation tests. {}'
            .format(ex)
        )
    yield desc

    for entity in [compute, storage]:
        try:
            entity.delete_if_exists()
        except Exception as ex:
            pytest.fail(
                'Exception cleaning up compute/storage rate for chargeback allocation tests. {}'
                .format(ex)
            )


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
    # The report generated through this automation contains only one row with chargeback costs
    # (since we only have C&U data for an hour and daily chargeback reports have one row per hour).
    # The second row contains the VM name only.
    # Hence, we are using index 0 to fetch the costs from the first row.
    if not chargeback_report_custom[0][column]:
        pytest.skip('missing column in report')
    else:
        estimated_resource_alloc_cost = chargeback_costs_custom[resource_alloc_cost]
        cost_from_report = chargeback_report_custom[0][column]
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(estimated_resource_alloc_cost - COST_DEVIATION <=
            float(cost) <= estimated_resource_alloc_cost + COST_DEVIATION,
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
    # The report generated through this automation contains only one row with chargeback costs
    # (since we only have C&U data for an hour and daily chargeback reports have one row per hour).
    # The second row contains the VM name only.
    # Hence, we are using index 0 to fetch the costs from the first row.
    if not chargeback_report_custom[0][column]:
        pytest.skip('missing column in report')
    else:
        allocated_resource = resource_alloc[resource]
        if ('GB' in chargeback_report_custom[0][column] and
                column == 'Memory Allocated over Time Period'):
            allocated_resource = allocated_resource * math.pow(2, -10)
        resource_from_report = chargeback_report_custom[0][column].replace(' ', '')
        resource_from_report = resource_from_report.replace('GB', '')
        resource_from_report = resource_from_report.replace('MB', '')
        lower_end = allocated_resource - RESOURCE_ALLOC_DEVIATION
        upper_end = allocated_resource + RESOURCE_ALLOC_DEVIATION
        soft_assert(lower_end <= float(resource_from_report) <= upper_end,
                    'Estimated resource allocation and report resource allocation do not match')


def test_verify_alloc_memory(resource_alloc, chargeback_report_custom, soft_assert):
    """Test to verify memory allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_resource_alloc(resource_alloc, chargeback_report_custom,
        'Memory Allocated over Time Period', 'memory_alloc', soft_assert)


def test_verify_alloc_cpu(resource_alloc, chargeback_report_custom, soft_assert):
    """Test to verify cpu allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_resource_alloc(resource_alloc, chargeback_report_custom,
        'vCPUs Allocated over Time Period', 'vcpu_alloc', soft_assert)


def test_verify_alloc_storage(resource_alloc, chargeback_report_custom, soft_assert):
    """Test to verify storage allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_resource_alloc(resource_alloc, chargeback_report_custom,
        'Storage Allocated', 'storage_alloc', soft_assert)


def test_validate_alloc_memory_cost(chargeback_costs_custom, chargeback_report_custom,
        soft_assert):
    """Test to validate cost for memory allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom,
        'Memory Allocated Cost', 'memory_alloc_cost', soft_assert)


def test_validate_alloc_vcpu_cost(chargeback_costs_custom, chargeback_report_custom,
        soft_assert):
    """Test to validate cost for vCPU allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom,
        'vCPUs Allocated Cost', 'vcpu_alloc_cost', soft_assert)


def test_validate_alloc_storage_cost(chargeback_costs_custom, chargeback_report_custom,
        soft_assert):
    """Test to validate cost for storage allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_chargeback_cost(chargeback_costs_custom, chargeback_report_custom,
        'Storage Allocated Cost', 'storage_alloc_cost', soft_assert)
