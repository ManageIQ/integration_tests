""" Tests to validate chargeback costs for daily, weekly, monthly rates.

All infra and cloud providers support chargeback reports.
But, in order to validate costs for different rates, running the tests on just one provider
should suffice.
"""
import math
from datetime import date

import fauxfactory
import pytest
from wrapanapi import VmState

import cfme.intelligence.chargeback.assignments as cb
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.parametrize('interval', ['Daily', 'Weekly', 'Monthly'],
        ids=['daily_rate', 'weekly_rate', 'monthly_rate'], scope='module'),
    pytest.mark.provider([RHEVMProvider], selector=ONE,
                       scope='module',
                       required_fields=[(['cap_and_util', 'test_chargeback'], True)]),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.chargeback,
]

# Allowed deviation between the reported value in the Chargeback report and the estimated value.
DEVIATION = 1

divisor = {
    'Daily': 24,
    'Weekly': 24 * 7,
    'Monthly': 24 * 30
}


@pytest.fixture(scope="module")
def vm_ownership(enable_candu, provider, appliance):
    """In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    assigned ownership.
    """
    collection = appliance.provider_based_collection(provider)
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    vm = collection.instantiate(vm_name, provider)
    if not vm.exists_on_provider:
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    vm.mgmt.ensure_state(VmState.RUNNING)

    group_collection = appliance.collections.groups
    cb_group = group_collection.instantiate(description='EvmGroup-user')

    # don't assume collection is infra, in case test collected against other provider types
    # No vm creation or cleanup
    user = appliance.collections.users.create(
        name='{}_{}'.format(provider.name, fauxfactory.gen_alphanumeric()),
        credential=Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
            secret='secret'),
        email='abc@example.com',
        groups=cb_group,
        cost_center='Workload',
        value_assign='Database')
    vm.set_ownership(user=user)
    logger.info('Assigned VM OWNERSHIP for {} running on {}'.format(vm_name, provider.name))
    yield user.name

    vm.unset_ownership()
    if user:
        user.delete()


@pytest.fixture(scope="module")
def enable_candu(appliance):
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


@pytest.fixture(scope="module")
def assign_custom_rate(new_compute_rate):
    """Assign custom Compute rate to the Enterprise and then queue the Chargeback report."""
    description = new_compute_rate
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


def verify_records_rollups_table(appliance, provider):
    """Verify that hourly rollups are present in the metric_rollups table."""
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
    """Verify that rollups are present in the metric_rollups table."""
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    ems = appliance.db.client['ext_management_systems']
    metrics = appliance.db.client['metrics']

    # Capture real-time C&U data
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_capture('realtime', 1.hour.ago.utc, Time.now.utc)\""
        .format(provider.id, repr(vm_name)))
    assert ret.success, "Failed to capture VM C&U data:".format(ret.output)

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
def resource_usage(vm_ownership, appliance, provider):
    """Retrieve resource usage values from metric_rollups table.

    Chargeback reporting is done on hourly and daily rollup values and not real-time values.So, we
    are capturing C&U data and forcing hourly rollups by running commands through
    the Rails console.
    """
    average_cpu_used_in_mhz = 0
    average_memory_used_in_mb = 0
    average_network_io = 0
    average_disk_io = 0
    average_storage_used = 0
    consumed_hours = 0
    vm_name = provider.data['cap_and_util']['chargeback_vm']

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
    assert ret.success, "Failed to rollup VM C&U data:".format(ret.out)

    wait_for(verify_records_rollups_table, [appliance, provider], timeout=600,
        message='Waiting for hourly rollups')

    # Since we are collecting C&U data for > 1 hour, there will be multiple hourly records per VM
    # in the metric_rollups DB table.The values from these hourly records are summed up.

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(rollups.capture_interval_name == 'hourly', rollups.resource_name == vm_name,
            ems.name == provider.name, rollups.timestamp >= date.today())
        )

    for record in appliance.db.client.session.query(rollups).filter(
            rollups.id.in_(result.subquery())):
        consumed_hours = consumed_hours + 1
        average_storage_used = average_storage_used + record.derived_vm_used_disk_storage
        if any([record.cpu_usagemhz_rate_average,
           record.cpu_usage_rate_average,
           record.derived_memory_used,
           record.net_usage_rate_average,
           record.disk_usage_rate_average]):
            average_cpu_used_in_mhz = average_cpu_used_in_mhz + record.cpu_usagemhz_rate_average
            average_memory_used_in_mb = average_memory_used_in_mb + record.derived_memory_used
            average_network_io = average_network_io + record.net_usage_rate_average
            average_disk_io = average_disk_io + record.disk_usage_rate_average

    # By default,chargeback rates for storage are defined in this form: 0.01 USD/GB
    # Hence,convert storage used in Bytes to GB
    average_storage_used = average_storage_used * math.pow(2, -30)

    return {"average_cpu_used_in_mhz": average_cpu_used_in_mhz,
            "average_memory_used_in_mb": average_memory_used_in_mb,
            "average_network_io": average_network_io,
            "average_disk_io": average_disk_io,
            "average_storage_used": average_storage_used,
            "consumed_hours": consumed_hours}


def resource_cost(appliance, metric_description, usage, description, rate_type,
        consumed_hours, interval):
    """Query the DB for Chargeback rates"""
    tiers = appliance.db.client['chargeback_tiers']
    details = appliance.db.client['chargeback_rate_details']
    cb_rates = appliance.db.client['chargeback_rates']
    list_of_rates = []

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(tiers)
            .join(details, tiers.chargeback_rate_detail_id == details.id)
            .join(cb_rates, details.chargeback_rate_id == cb_rates.id)
            .filter(details.description == metric_description)
            .filter(cb_rates.rate_type == rate_type)
            .filter(cb_rates.description == description).all()
        )
    for row in result:
        tiered_rate = {var: getattr(row, var) for var in ['variable_rate', 'fixed_rate', 'start',
            'finish']}
        list_of_rates.append(tiered_rate)

    # Check what tier the usage belongs to and then compute the usage cost based on Fixed and
    # Variable Chargeback rates.
    for rate in list_of_rates:
        if usage >= rate['start'] and usage < rate['finish']:
            cost = ((rate['variable_rate'] * usage) +
                (rate['fixed_rate'] * consumed_hours)) / divisor[interval]
            return cost


@pytest.fixture(scope="module")
def chargeback_costs_custom(resource_usage, new_compute_rate, appliance, interval):
    """Estimate Chargeback costs using custom Chargeback rate and resource usage from the DB."""
    description = new_compute_rate

    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']
    average_storage_used = resource_usage['average_storage_used']
    consumed_hours = resource_usage['consumed_hours']

    cpu_used_cost = resource_cost(appliance, 'Used CPU',
        average_cpu_used_in_mhz, description, 'Compute', consumed_hours, interval)

    memory_used_cost = resource_cost(appliance, 'Used Memory',
        average_memory_used_in_mb, description, 'Compute', consumed_hours, interval)

    network_used_cost = resource_cost(appliance, 'Used Network I/O',
        average_network_io, description, 'Compute', consumed_hours, interval)

    disk_used_cost = resource_cost(appliance, 'Used Disk I/O',
        average_disk_io, description, 'Compute', consumed_hours, interval)

    storage_used_cost = resource_cost(appliance, 'Used Disk Storage',
        average_storage_used, description, 'Storage', consumed_hours, interval)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost,
            "storage_used_cost": storage_used_cost}


@pytest.fixture(scope="module")
def chargeback_report_custom(appliance, vm_ownership, assign_custom_rate, interval):
    """Create a Chargeback report based on a custom rate; Queue the report"""
    owner = vm_ownership
    data = {
        'menu_name': interval,
        'title': interval,
        'base_report_on': 'Chargeback for Vms',
        'report_fields': ['Memory Used', 'Memory Used Cost', 'Owner',
        'CPU Used', 'CPU Used Cost',
        'Disk I/O Used', 'Disk I/O Used Cost',
        'Network I/O Used', 'Network I/O Used Cost',
        'Storage Used', 'Storage Used Cost'],
        'filter': {
            'filter_show_costs': 'Owner',
            'filter_owner': owner,
            'interval_end': 'Today (partial)'
        }
    }
    report = appliance.collections.reports.create(is_candu=True, **data)

    logger.info('Queuing chargeback report for {} rate'.format(interval))
    report.queue(wait_for_finish=True)

    if not list(report.saved_reports.all()[0].data.rows):
        pytest.skip('Empty report')
    else:
        yield list(report.saved_reports.all()[0].data.rows)

    if report.exists:
        report.delete()


@pytest.fixture(scope="module")
def new_compute_rate(appliance, interval):
    """Create a new Compute Chargeback rate"""
    desc = fauxfactory.gen_alphanumeric(20, start=f"custom_{interval}")
    try:
        compute = appliance.collections.compute_rates.create(
            description=desc,
            fields={
                'Used CPU': {'per_time': interval, 'variable_rate': '720'},
                'Used Disk I/O': {'per_time': interval, 'variable_rate': '720'},
                'Used Network I/O': {'per_time': interval, 'variable_rate': '720'},
                'Used Memory': {'per_time': interval, 'variable_rate': '720'}
            }
        )
        storage = appliance.collections.storage_rates.create(
            description=desc,
            fields={
                'Used Disk Storage': {'per_time': interval, 'variable_rate': '720'}
            }
        )
    except Exception as ex:
        pytest.fail(
            'Exception while creating compute/storage rates for chargeback long term rate tests. {}'
            .format(ex)
        )
    yield desc

    for entity in [compute, storage]:
        try:
            entity.delete_if_exists()
        except Exception as ex:
            pytest.fail(
                'Exception cleaning up compute/storage rate for chargeback long term rate tests. {}'
                .format(ex)
            )


def test_validate_cpu_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider, soft_assert):
    """Test to validate CPU usage cost reported in chargeback reports.
    The cost reported in the Chargeback report should be approximately equal to the
    cost estimated in the chargeback_costs_custom fixture.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    if not chargeback_report_custom[0]["CPU Used Cost"]:
        pytest.skip('missing column in report')
    else:
        estimated_cpu_usage_cost = chargeback_costs_custom['cpu_used_cost']
        cost_from_report = chargeback_report_custom[0]["CPU Used Cost"]
        # Eliminate '$' and ',' from string
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(estimated_cpu_usage_cost - DEVIATION <=
            float(cost) <= estimated_cpu_usage_cost + DEVIATION,
            'Estimated cost and report cost do not match')


def test_validate_memory_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider, soft_assert):
    """Test to validate memory usage cost reported in chargeback reports.
    The cost reported in the Chargeback report should be approximately equal to the
    cost estimated in the chargeback_costs_custom fixture.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    if not chargeback_report_custom[0]["Memory Used Cost"]:
        pytest.skip('missing column in report')
    else:
        estimated_memory_usage_cost = chargeback_costs_custom['memory_used_cost']
        cost_from_report = chargeback_report_custom[0]["Memory Used Cost"]
        # Eliminate '$' and ',' from string
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(estimated_memory_usage_cost - DEVIATION <=
            float(cost) <= estimated_memory_usage_cost + DEVIATION,
            'Estimated cost and report cost do not match')


def test_validate_network_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider, soft_assert):
    """Test to validate network usage cost reported in chargeback reports.
    The cost reported in the Chargeback report should be approximately equal to the
    cost estimated in the chargeback_costs_custom fixture.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    if not chargeback_report_custom[0]["Network I/O Used Cost"]:
        pytest.skip('missing column in report')
    else:
        estimated_network_usage_cost = chargeback_costs_custom['network_used_cost']
        cost_from_report = chargeback_report_custom[0]["Network I/O Used Cost"]
        # Eliminate '$' and ',' from string
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(estimated_network_usage_cost - DEVIATION <=
            float(cost) <= estimated_network_usage_cost + DEVIATION,
            'Estimated cost and report cost do not match')


def test_validate_disk_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider, soft_assert):
    """Test to validate disk usage cost reported in chargeback reports.
    The cost reported in the Chargeback report should be approximately equal to the
    cost estimated in the chargeback_costs_custom fixture.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    if not chargeback_report_custom[0]["Disk I/O Used Cost"]:
        pytest.skip('missing column in report')
    else:
        estimated_disk_usage_cost = chargeback_costs_custom['disk_used_cost']
        cost_from_report = chargeback_report_custom[0]["Disk I/O Used Cost"]
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(estimated_disk_usage_cost - DEVIATION <=
            float(cost) <= estimated_disk_usage_cost + DEVIATION,
            'Estimated cost and report cost do not match')


def test_validate_storage_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider, soft_assert):
    """Test to validate storage usage cost reported in chargeback reports.
    The cost reported in the Chargeback report should be approximately equal to the
    cost estimated in the chargeback_costs_custom fixture.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    if not chargeback_report_custom[0]["Storage Used Cost"]:
        pytest.skip('missing column in report')
    else:
        estimated_storage_usage_cost = chargeback_costs_custom['storage_used_cost']
        cost_from_report = chargeback_report_custom[0]["Storage Used Cost"]
        cost = cost_from_report.replace('$', '').replace(',', '')
        soft_assert(estimated_storage_usage_cost - DEVIATION <=
            float(cost) <= estimated_storage_usage_cost + DEVIATION,
            'Estimated cost and report cost do not match')
