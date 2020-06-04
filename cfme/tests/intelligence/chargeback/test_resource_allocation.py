"""Validate resource allocation values and costs in chargeback reports, for VM/Instance allocated
memory, CPU, and storage. Resource usage validation tests are in
cfme/tests/intelligence/reports/test_validate_chargeback_report.py.

TODO: Verify whether this is still an issue:

Note: When the tests were parameterized, it was observed that the fixture scope was not preserved in
parametrized tests. This is supposed to be a known pytest bug.

This test module has a few module-scoped fixtures that actually get invoked for every parameterized
test, despite the fact that these fixtures are module-scoped. So, the tests have not been
parameterized.
"""
from datetime import date
from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.intelligence.chargeback.assignments import ComputeAssign
from cfme.intelligence.chargeback.assignments import StorageAssign
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.long_running,
    pytest.mark.provider([CloudProvider, InfraProvider], scope='module', selector=ONE_PER_TYPE,
                         required_fields=[(['cap_and_util', 'test_chargeback'], True)]),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
    pytest.mark.meta(blockers=[BZ(1843942, forced_streams=['5.11'],
        unblock=lambda provider: not provider.one_of(AzureProvider))])
]

# Allowed deviations between chargeback report values and estimated values.
COST_DEVIATION = 1
"""Allowed deviation for the resource allocation cost"""
RESOURCE_ALLOC_DEVIATION = 0.25
"""Allowed deviation for the resource allocation value"""


@pytest.fixture(scope='module')
def chargeback_vm(provider):
    return provider.data['cap_and_util']['chargeback_vm']


@pytest.fixture(scope='module')
def vm_owner(enable_candu, provider, appliance, chargeback_vm):
    """Create and assign owner to VM, for use in chargeback report filter."""
    vm_name = chargeback_vm
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


@pytest.fixture(scope='module')
def enable_candu(provider, appliance):
    """Enable C&U server roles, and disable resource-intensive server roles while performing
    metric capture."""
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


@pytest.fixture(scope='module')
def assign_chargeback_rate(chargeback_rate):
    """Assign chargeback rates to the Enterprise and then queue the Chargeback report."""
    description = chargeback_rate
    # TODO Move this to a global fixture
    for cls in (ComputeAssign, StorageAssign):
        enterprise = cls(
            assign_to="The Enterprise",
            selections={
                'Enterprise': {'Rate': description}
            })
        enterprise.assign()
    logger.info(f"Assigned chargeback rates {chargeback_rate}")
    yield

    # Resetting the Chargeback rate assignment
    for cls in (ComputeAssign, StorageAssign):
        enterprise = cls(
            assign_to="The Enterprise",
            selections={
                'Enterprise': {'Rate': '<Nothing>'}
            })
        enterprise.assign()


def verify_vm_uptime(appliance, vm_name):
    """Verify VM uptime is at least one hour. That is the shortest duration for
    which VMs can be charged.
    """
    vm_creation_time = appliance.rest_api.collections.vms.get(name=vm_name).created_on
    return appliance.utc_time() - vm_creation_time > timedelta(hours=1)


def verify_records_rollups_table(appliance, provider, chargeback_vm):
    """Verify that hourly rollups are present in the metric_rollups table."""
    ems = appliance.db.client['ext_management_systems']
    rollups = appliance.db.client['metric_rollups']

    retval = False
    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(
                rollups.capture_interval_name == 'hourly',
                rollups.resource_name == chargeback_vm,
                ems.name == provider.name,
                rollups.timestamp >= date.today())
        )

        for record in appliance.db.client.session.query(rollups).filter(
                rollups.id.in_(result.subquery())):
            if any([
                    record.cpu_usagemhz_rate_average,
                    record.cpu_usage_rate_average,
                    record.derived_memory_used,
                    record.net_usage_rate_average,
                    record.disk_usage_rate_average]):
                retval = True
    return retval


def verify_records_metrics_table(appliance, provider, chargeback_vm):
    """Verify that realtime metrics are present in the metrics table."""
    ems = appliance.db.client['ext_management_systems']
    metrics = appliance.db.client['metrics']

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(metrics.id)
            .join(ems, metrics.parent_ems_id == ems.id)
            .filter(
                metrics.capture_interval_name == 'realtime',
                metrics.resource_name == chargeback_vm,
                ems.name == provider.name,
                metrics.timestamp >= date.today())
        )

        for record in appliance.db.client.session.query(metrics).filter(
                metrics.id.in_(result.subquery())):
            return any([
                record.cpu_usagemhz_rate_average,
                record.cpu_usage_rate_average,
                record.derived_memory_used,
                record.net_usage_rate_average,
                record.disk_usage_rate_average])
    return False


@pytest.fixture(scope='module')
def resource_alloc(vm_owner, appliance, provider, chargeback_vm):
    """Retrieve resource allocation values."""
    metrics = appliance.db.client['metrics']
    rollups = appliance.db.client['metric_rollups']
    vim_performance_states = appliance.db.client['vim_performance_states']
    ems = appliance.db.client['ext_management_systems']

    logger.info("Deleting data from metrics, metric_rollups, and vim_performance_states tables.")

    with appliance.db.client.transaction:
        for table in (metrics, rollups, vim_performance_states):
            appliance.db.client.session.query(table).delete()

    logger.info("Capturing realtime C&U data.")
    ret = appliance.ssh_client.run_rails_command(
        f"\"vm = Vm.where(:ems_id => {provider.id}).where(:name => {chargeback_vm!r})[0];"
        "vm.perf_capture('realtime', 1.hour.ago.utc, Time.now.utc)\"")
    assert ret.success, f"Failed to capture C&U data for VM {chargeback_vm!r}."

    wait_for(verify_records_metrics_table, [appliance, provider, chargeback_vm], timeout=600,
        message='Waiting for VM realtime data')

    # New C&U data may sneak in since 1)C&U server roles are running and 2)collection for clusters
    # and hosts is on.This would mess up our Chargeback calculations, so we are disabling C&U
    # collection after data has been fetched for the last hour.

    appliance.server.settings.disable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector')

    # Perform rollup of C&U data.
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_rollup_range(1.hour.ago.utc, Time.now.utc,'realtime')\"".
        format(provider.id, repr(chargeback_vm)))
    assert ret.success, f"Failed to rollup VM C&U data:"

    wait_for(verify_records_rollups_table, [appliance, provider, chargeback_vm], timeout=600,
        message='Waiting for hourly rollups')

    # Since we are collecting C&U data for > 1 hour, there will be multiple hourly records per VM
    # in the metric_rollups DB table. The values from these hourly records are summed up.
    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(
                rollups.capture_interval_name == 'hourly',
                rollups.resource_name == chargeback_vm,
                ems.name == provider.name,
                rollups.timestamp >= date.today())
        )
        for record in appliance.db.client.session.query(rollups).filter(
                rollups.id.in_(result.subquery())):
            if all([
                record.derived_vm_numvcpus,
                record.derived_memory_available,
                record.derived_vm_allocated_disk_storage
            ]):
                break

    # By default, chargeback rates for storage are defined in this form: 0.01 USD/GB
    # Convert metric value from Bytes to GB.

    storage_alloc = float(record.derived_vm_allocated_disk_storage or 0)
    return {
        'vcpu_alloc': float(record.derived_vm_numvcpus or 0),
        'memory_alloc': float(record.derived_memory_available or 0),
        'storage_alloc': storage_alloc * 2**-30}


def resource_cost(appliance, provider, metric_description, alloc_value, num_hours,
        description, rate_type):
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
            tiered_rate = {var: getattr(row, var) for var in [
                'variable_rate',
                'fixed_rate',
                'start',
                'finish']}
            list_of_rates.append(tiered_rate)

    # Find the matching tier for this resource allocation value and then compute the estimated
    # cost based on the fixed and variable rate values.
    for d in list_of_rates:
        if d['start'] <= alloc_value < d['finish']:
            cost = (d['variable_rate'] * alloc_value + d['fixed_rate']) * num_hours
            return cost


@pytest.fixture(scope='module')
def chargeback_costs(resource_alloc, chargeback_rate, appliance, provider, chargeback_vm):
    """Estimate chargeback costs using chargeback rate and resource allocation"""
    description = chargeback_rate
    storage_alloc = resource_alloc['storage_alloc']
    memory_alloc = resource_alloc['memory_alloc']
    vcpu_alloc = resource_alloc['vcpu_alloc']

    vm = appliance.provider_based_collection(provider, coll_type='vms').instantiate(chargeback_vm,
        provider)
    state_changed_on = vm.rest_api_entity.state_changed_on.replace(tzinfo=None)

    now = datetime.utcnow()
    beginning_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate the number of hours to be used when estimating costs.
    if state_changed_on > beginning_of_day:
        beginning_of_hour = now.replace(minute=0, second=0, microsecond=0)
        if state_changed_on > beginning_of_hour:
            num_hours = 1
        else:
            num_hours = (beginning_of_hour - state_changed_on).total_seconds() // 3600
    else:
        num_hours = now.hour

    logger.info(f"num_hours = {num_hours}")
    storage_alloc_cost = resource_cost(appliance, provider, 'Allocated Disk Storage',
        storage_alloc, num_hours, description, 'Storage')

    memory_alloc_cost = resource_cost(appliance, provider, 'Allocated Memory',
        memory_alloc, num_hours, description, 'Compute')

    vcpu_alloc_cost = resource_cost(appliance, provider, 'Allocated CPU Count',
        vcpu_alloc, num_hours, description, 'Compute')

    return {
        'storage_alloc_cost': storage_alloc_cost,
        'memory_alloc_cost': memory_alloc_cost,
        'vcpu_alloc_cost': vcpu_alloc_cost}


@pytest.fixture(scope='module')
def chargeback_report(appliance, vm_owner, assign_chargeback_rate, provider):
    """Create a chargeback report and then queue it."""
    owner = vm_owner
    data = {
        'menu_name': f'{provider.name}_{fauxfactory.gen_alphanumeric()}',
        'title': f'{provider.name}_{fauxfactory.gen_alphanumeric()}',
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

    logger.info(f"Queuing chargeback report for provider {provider.name!r}.")
    report.queue(wait_for_finish=True)

    if not list(report.saved_reports.all()[0].data.rows):
        pytest.skip('Empty report')
    else:
        yield list(report.saved_reports.all()[0].data.rows)

    if report.exists:
        report.delete()


@pytest.fixture(scope='module')
def chargeback_rate(appliance):
    """Create a new chargeback rate"""
    desc = fauxfactory.gen_alphanumeric(15, start="cb_")
    try:
        compute = appliance.collections.compute_rates.create(
            description=desc,
            fields={
                'Allocated CPU Count': {
                    'per_time': 'Hourly',
                    'fixed_rate': '1.0',
                    'variable_rate': '2.0'
                },
                'Allocated Memory': {
                    'per_time': 'Hourly',
                    'fixed_rate': '0.0',
                    'variable_rate': '2.0'
                }
            }
        )
        storage = appliance.collections.storage_rates.create(
            description=desc,
            fields={
                'Allocated Disk Storage': {
                    'per_time': 'Hourly',
                    'fixed_rate': '1.0',
                    'variable_rate': '3.0'
                }
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


def generic_test_chargeback_cost(chargeback_costs, chargeback_report, column,
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
    if not chargeback_report[0][column]:
        pytest.skip('missing column in report')
    else:
        estimated_cost = chargeback_costs[resource_alloc_cost]
        cost_from_report = chargeback_report[0][column]
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(
            estimated_cost - COST_DEVIATION <= float(cost) <= estimated_cost + COST_DEVIATION,
            f"Estimated cost {estimated_cost} and report cost {cost} do not match")


def generic_test_resource_alloc(resource_alloc, chargeback_report, column,
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
    if not chargeback_report[0][column]:
        pytest.skip('missing column in report')
    else:
        allocated_resource = resource_alloc[resource]
        if ('GB' in chargeback_report[0][column] and
                column == 'Memory Allocated over Time Period'):
            allocated_resource = allocated_resource * 2**-10
        resource_from_report = chargeback_report[0][column].replace(' ', '')
        resource_from_report = resource_from_report.replace('GB', '')
        resource_from_report = resource_from_report.replace('MB', '')
        lower_end = allocated_resource - RESOURCE_ALLOC_DEVIATION
        upper_end = allocated_resource + RESOURCE_ALLOC_DEVIATION
        soft_assert(lower_end <= float(resource_from_report) <= upper_end,
                    'Estimated resource allocation and report resource allocation do not match')


def test_verify_alloc_memory(resource_alloc, chargeback_report, soft_assert):
    """Test to verify memory allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_resource_alloc(resource_alloc, chargeback_report,
        'Memory Allocated over Time Period', 'memory_alloc', soft_assert)


def test_verify_alloc_cpu(resource_alloc, chargeback_report, soft_assert):
    """Test to verify cpu allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_resource_alloc(resource_alloc, chargeback_report,
        'vCPUs Allocated over Time Period', 'vcpu_alloc', soft_assert)


def test_verify_alloc_storage(resource_alloc, chargeback_report, soft_assert):
    """Test to verify storage allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_resource_alloc(resource_alloc, chargeback_report,
        'Storage Allocated', 'storage_alloc', soft_assert)


def test_validate_alloc_memory_cost(chargeback_costs, chargeback_report, soft_assert):
    """Test to validate cost for memory allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_chargeback_cost(chargeback_costs, chargeback_report,
        'Memory Allocated Cost', 'memory_alloc_cost', soft_assert)


def test_validate_alloc_vcpu_cost(chargeback_costs, chargeback_report, soft_assert):
    """Test to validate cost for vCPU allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_chargeback_cost(chargeback_costs, chargeback_report,
        'vCPUs Allocated Cost', 'vcpu_alloc_cost', soft_assert)


def test_validate_alloc_storage_cost(chargeback_costs, chargeback_report, soft_assert):
    """Test to validate cost for storage allocation

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: CandU
    """
    generic_test_chargeback_cost(chargeback_costs, chargeback_report,
        'Storage Allocated Cost', 'storage_alloc_cost', soft_assert)
