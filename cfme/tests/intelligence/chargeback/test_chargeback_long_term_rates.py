# -*- coding: utf-8 -*-

import math
from datetime import date

import fauxfactory
import pytest
import re

import cfme.intelligence.chargeback.assignments as cb
import cfme.intelligence.chargeback.rates as rates
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.provider import BaseProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.intelligence.reports.reports import CustomReport
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from fixtures.provider import setup_or_skip

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.parametrize('interval', ['Daily', 'Weekly', 'Monthly'],
        ids=['daily_rate', 'weekly_rate', 'monthly_rate'], scope='module'),
    pytest.mark.provider([RHEVMProvider],
                       scope='module',
                       required_fields=[(['cap_and_util', 'test_chargeback'], True)]),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
]


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='secret')


@pytest.yield_fixture(scope="module")
def vm_ownership(enable_candu, provider, appliance):
    # In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    # assigned ownership.
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    if not provider.mgmt.does_vm_exist(vm_name):
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    if not provider.mgmt.is_vm_running(vm_name):
        provider.mgmt.start_vm(vm_name)
        provider.mgmt.wait_vm_running(vm_name)

    group_collection = appliance.collections.groups
    cb_group = group_collection.instantiate(description='EvmGroup-user')

    vm = VM.factory(vm_name, provider)
    user = None
    try:
        user = appliance.collections.users.create(
            name=provider.name + fauxfactory.gen_alphanumeric(),
            credential=new_credential(),
            email='abc@example.com',
            groups=cb_group,
            cost_center='Workload',
            value_assign='Database')
        vm.set_ownership(user=user.name)
        logger.info('Assigned VM OWNERSHIP for {} running on {}'.format(vm_name, provider.name))

        yield user.name
    finally:
        vm.unset_ownership()
        if user:
            user.delete()


@pytest.yield_fixture(scope="module")
def enable_candu(appliance):
    # C&U data collection consumes a lot of memory and CPU.So, we are disabling some server roles
    # that are not needed for Chargeback reporting.

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
def assign_custom_rate(new_compute_rate):
    # Assign custom Compute rate to the Enterprise and then queue the Chargeback report.
    description = new_compute_rate
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


def verify_records_rollups_table(appliance, provider):
    # Verify that hourly rollups are present in the metric_rollups table.
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
        if (record.cpu_usagemhz_rate_average or
           record.cpu_usage_rate_average or
           record.derived_memory_used or
           record.net_usage_rate_average or
           record.disk_usage_rate_average):
            return True
    return False


@pytest.fixture(scope="module")
def resource_usage(vm_ownership, appliance, provider):
    # Retrieve resource usage values from metric_rollups table.
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

    # Chargeback reporting is done on hourly and daily rollup values and not real-time values.So, we
    # are capturing C&U data and forcing hourly rollups by running these commands through
    # the Rails console.

    def verify_records_metrics_table(appliance, provider):
        # Verify that rollups are present in the metric_rollups table.
        vm_name = provider.data['cap_and_util']['chargeback_vm']

        ems = appliance.db.client['ext_management_systems']
        metrics = appliance.db.client['metrics']

        rc, out = appliance.ssh_client.run_rails_command(
            "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
            vm.perf_capture('realtime', 1.hour.ago.utc, Time.now.utc)\""
            .format(provider.id, repr(vm_name)))
        assert rc == 0, "Failed to capture VM C&U data:".format(out)

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
            if (record.cpu_usagemhz_rate_average or
               record.cpu_usage_rate_average or
               record.derived_memory_used or
               record.net_usage_rate_average or
               record.disk_usage_rate_average):
                return True
        return False

    wait_for(verify_records_metrics_table, [appliance, provider], timeout=600,
        fail_condition=False, message='Waiting for VM real-time data')

    # New C&U data may sneak in since 1)C&U server roles are running and 2)collection for clusters
    # and hosts is on.This would mess up our Chargeback calculations, so we are disabling C&U
    # collection after data has been fetched for the last hour.

    appliance.server.settings.disable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector')
    rc, out = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_rollup_range(1.hour.ago.utc, Time.now.utc,'realtime')\"".
        format(provider.id, repr(vm_name)))
    assert rc == 0, "Failed to rollup VM C&U data:".format(out)

    wait_for(verify_records_rollups_table, [appliance, provider], timeout=600, fail_condition=False,
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
        if (record.cpu_usagemhz_rate_average or
           record.cpu_usage_rate_average or
           record.derived_memory_used or
           record.net_usage_rate_average or
           record.disk_usage_rate_average):
            average_cpu_used_in_mhz = average_cpu_used_in_mhz + record.cpu_usagemhz_rate_average
            average_memory_used_in_mb = average_memory_used_in_mb + record.derived_memory_used
            average_network_io = average_network_io + record.net_usage_rate_average
            average_disk_io = average_disk_io + record.disk_usage_rate_average

    for record in appliance.db.client.session.query(rollups).filter(
            rollups.id.in_(result.subquery())):
        if record.derived_vm_used_disk_storage:
            average_storage_used = average_storage_used + record.derived_vm_used_disk_storage

    # Convert storage used in Bytes to GB
    average_storage_used = average_storage_used * math.pow(2, -30)

    return {"average_cpu_used_in_mhz": average_cpu_used_in_mhz,
            "average_memory_used_in_mb": average_memory_used_in_mb,
            "average_network_io": average_network_io,
            "average_disk_io": average_disk_io,
            "average_storage_used": average_storage_used,
            "consumed_hours": consumed_hours}


def resource_cost(appliance, metric_description, usage, description, rate_type,
        consumed_hours, interval):
    # Query the DB for Chargeback rates
    tiers = appliance.db.client['chargeback_tiers']
    details = appliance.db.client['chargeback_rate_details']
    cb_rates = appliance.db.client['chargeback_rates']
    list_of_rates = []

    def add_rate(tiered_rate):
        list_of_rates.append(tiered_rate)

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
        add_rate(tiered_rate)

    # Check what tier the usage belongs to and then compute the usage cost based on Fixed and
    # Variable Chargeback rates.
    for d in list_of_rates:
        if usage >= d['start'] and usage < d['finish']:
            if interval == 'Daily':
                cost = ((d['variable_rate'] * usage) + (d['fixed_rate'] * consumed_hours)) / 24
            elif interval == 'Weekly':
                cost = ((d['variable_rate'] * usage) +
                    d['fixed_rate'] * consumed_hours)) / (24 * 7)
            elif interval == 'Monthly':
                cost = ((d['variable_rate'] * usage) +
                    (d['fixed_rate'] * consumed_hours)) / (24 * 30)
            return cost


@pytest.fixture(scope="module")
def chargeback_costs_custom(resource_usage, new_compute_rate, appliance):
    # Estimate Chargeback costs using custom Chargeback rate and resource usage from the DB.
    description = new_compute_rate

    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']
    average_storage_used = resource_usage['average_storage_used']
    consumed_hours = resource_usage['consumed_hours']

    cpu_used_cost = resource_cost(appliance, 'Used CPU',
        average_cpu_used_in_mhz, description, 'Compute', consumed_hours)

    memory_used_cost = resource_cost(appliance, 'Used Memory',
        average_memory_used_in_mb, description, 'Compute', consumed_hours)

    network_used_cost = resource_cost(appliance, 'Used Network I/O',
        average_network_io, description, 'Compute', consumed_hours)

    disk_used_cost = resource_cost(appliance, 'Used Disk I/O',
        average_disk_io, description, 'Compute', consumed_hours)

    storage_used_cost = resource_cost(appliance, 'Used Disk Storage',
        average_storage_used, description, 'Storage', consumed_hours)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost,
            "storage_used_cost": storage_used_cost}


@pytest.yield_fixture(scope="module")
def chargeback_report_custom(vm_ownership, assign_custom_rate, interval):
    # Create a Chargeback report based on a custom rate; Queue the report
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
    report = CustomReport(is_candu=True, **data)
    report.create()

    logger.info('Queuing chargeback report for {} rate'.format(interval))
    report.queue(wait_for_finish=True)

    yield list(report.get_saved_reports()[0].data.rows)
    # report.delete()


@pytest.yield_fixture(scope="module")
def new_compute_rate(interval):
    # Create a new Compute Chargeback rate
    try:
        desc = 'custom_' + interval
        compute = rates.ComputeRate(description=desc,
                    fields={'Used CPU':
                            {'per_time': interval, 'variable_rate': '720'},
                            'Used Disk I/O':
                            {'per_time': interval, 'variable_rate': '720'},
                            'Used Memory':
                            {'per_time': interval, 'variable_rate': '720'}})
        compute.create()
        storage = rates.StorageRate(description=desc,
                    fields={'Used Disk Storage':
                            {'per_time': interval, 'variable_rate': '720'}})
        storage.create()
        yield desc
    finally:
        compute.delete()
        storage.delete()


# Tests to validate costs reported in the Chargeback report for various metrics.
# The costs reported in the Chargeback report should be approximately equal to the
# costs estimated in the chargeback_costs_default/chargeback_costs_custom fixtures.
def test_validate_cpu_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider):
    """Test to validate CPU usage cost.Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["CPU Used Cost"]:
            estimated_cpu_usage_cost = chargeback_costs_custom['cpu_used_cost']
            cost_from_report = groups["CPU Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_cpu_usage_cost - 1.0 <= float(cost) \
                <= estimated_cpu_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_memory_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider):
    """Test to validate memory usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["Memory Used Cost"]:
            estimated_memory_usage_cost = chargeback_costs_custom['memory_used_cost']
            cost_from_report = groups["Memory Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_memory_usage_cost - 1.0 <= float(cost) \
                <= estimated_memory_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_network_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider):
    """Test to validate network usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["Network I/O Used Cost"]:
            estimated_network_usage_cost = chargeback_costs_custom['network_used_cost']
            cost_from_report = groups["Network I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_network_usage_cost - 1.0 <= float(cost) \
                <= estimated_network_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_disk_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider):
    """Test to validate disk usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["Disk I/O Used Cost"]:
            estimated_disk_usage_cost = chargeback_costs_custom['disk_used_cost']
            cost_from_report = groups["Disk I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_disk_usage_cost - 1.0 <= float(cost) \
                <= estimated_disk_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_storage_usage_cost(chargeback_costs_custom, chargeback_report_custom,
        interval, provider):
    """Test to validate stoarge usage cost.
       Calculation is based on custom Chargeback rate.
    """
    for groups in chargeback_report_custom:
        if groups["Storage Used Cost"]:
            estimated_storage_usage_cost = chargeback_costs_custom['storage_used_cost']
            cost_from_report = groups["Storage Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_storage_usage_cost - 1.0 <= float(cost) \
                <= estimated_storage_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break
