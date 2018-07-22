# -*- coding: utf-8 -*-
#
""" Chargeback reports are supported for all infra and cloud providers.

Chargeback reports report costs based on 1)resource usage, 2)resource allocation
Costs are reported for the usage of the following resources by VMs:
memory, cpu, network io, disk io, storage.
Costs are reported for the allocation of the following resources to VMs:
memory, cpu, storage

So, for a provider such as VMware that supports C&U, a chargeback report would show costs for both
resource usage and resource allocation.

But, for a provider such as SCVMM that doesn't support C&U,chargeback reports show costs for
resource allocation only.

The tests in this module validate costs for resource usage.

The tests for resource allocation are in :
cfme/tests/intelligence/chargeback/test_resource_allocation.py
"""

import math
from datetime import date

import fauxfactory
import pytest
import re

import cfme.intelligence.chargeback.assignments as cb
import cfme.intelligence.chargeback.rates as rates
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.provider import CloudInfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for

from wrapanapi import VmState

pf1 = ProviderFilter(classes=[CloudInfraProvider],
    required_fields=[(['cap_and_util', 'test_chargeback'], True)])
pf2 = ProviderFilter(classes=[SCVMMProvider], inverted=True)  # SCVMM doesn't support C&U

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.meta(blockers=[BZ(1511099, forced_streams=['5.9', '5.8'],
                                  unblock=lambda provider: not provider.one_of(GCEProvider)),
                               ]),
    pytest.mark.provider(gen_func=providers, filters=[pf1, pf2], scope='module'),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
]

# Allowed deviation between the reported value in the Chargeback report and the estimated value.
DEVIATION = 1


@pytest.fixture(scope="module")
def vm_ownership(enable_candu, provider, appliance):
    # In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    # assigned ownership.
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(vm_name, provider)

    if not vm.exists_on_provider:
        pytest.skip("Skipping test, cu-24x7 VM does not exist")
    vm.mgmt.ensure_state(VmState.RUNNING)

    group_collection = appliance.collections.groups
    cb_group = group_collection.instantiate(description='EvmGroup-user')

    # No vm creation or cleanup
    user = None
    try:
        user = appliance.collections.users.create(
            name=provider.name + fauxfactory.gen_alphanumeric(),
            credential=Credential(principal='uid' + '{}'.format(fauxfactory.gen_alphanumeric()),
                secret='secret'),
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


@pytest.fixture(scope="module")
def enable_candu(provider, appliance):
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


@pytest.fixture(scope="module")
def assign_default_rate(provider):
    # Assign default Compute rate to the Enterprise and then queue the Chargeback report.
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })
    enterprise.computeassign()
    enterprise.storageassign()
    logger.info('Assigning DEFAULT Compute rate')

    yield

    # Resetting the Chargeback rate assignment
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': '<Nothing>'}
        })
    enterprise.computeassign()
    enterprise.storageassign()


@pytest.fixture(scope="module")
def assign_custom_rate(new_compute_rate, provider):
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

        result = appliance.ssh_client.run_rails_command(
            "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
            vm.perf_capture('realtime', 1.hour.ago.utc, Time.now.utc)\""
            .format(provider.id, repr(vm_name)))
        assert result.success, "Failed to capture VM C&U data:".format(result.output)

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
    result = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_rollup_range(1.hour.ago.utc, Time.now.utc,'realtime')\"".
        format(provider.id, repr(vm_name)))
    assert result.success, "Failed to rollup VM C&U data:".format(result.output)

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

    # Convert storage used in bytes to GB
    average_storage_used = average_storage_used * math.pow(2, -30)

    return {"average_cpu_used_in_mhz": average_cpu_used_in_mhz,
            "average_memory_used_in_mb": average_memory_used_in_mb,
            "average_network_io": average_network_io,
            "average_disk_io": average_disk_io,
            "average_storage_used": average_storage_used,
            "consumed_hours": consumed_hours}


def resource_cost(appliance, provider, metric_description, usage, description, rate_type,
        consumed_hours):
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
            cost = (d['variable_rate'] * usage) + (d['fixed_rate'] * consumed_hours)
            return cost


@pytest.fixture(scope="module")
def chargeback_costs_default(resource_usage, appliance, provider):
    # Estimate Chargeback costs using default Chargeback rate and resource usage from the DB.
    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']
    average_storage_used = resource_usage['average_storage_used']
    consumed_hours = resource_usage['consumed_hours']

    cpu_used_cost = resource_cost(appliance, provider, 'Used CPU',
        average_cpu_used_in_mhz, 'Default', 'Compute', consumed_hours)

    memory_used_cost = resource_cost(appliance, provider, 'Used Memory',
        average_memory_used_in_mb, 'Default', 'Compute', consumed_hours)

    network_used_cost = resource_cost(appliance, provider, 'Used Network I/O',
        average_network_io, 'Default', 'Compute', consumed_hours)

    disk_used_cost = resource_cost(appliance, provider, 'Used Disk I/O',
        average_disk_io, 'Default', 'Compute', consumed_hours)

    storage_used_cost = resource_cost(appliance, provider, 'Used Disk Storage',
        average_storage_used, 'Default', 'Storage', consumed_hours)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost,
            "storage_used_cost": storage_used_cost}


@pytest.fixture(scope="module")
def chargeback_costs_custom(resource_usage, new_compute_rate, appliance, provider):
    # Estimate Chargeback costs using custom Chargeback rate and resource usage from the DB.
    description = new_compute_rate

    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']
    average_storage_used = resource_usage['average_storage_used']
    consumed_hours = resource_usage['consumed_hours']

    cpu_used_cost = resource_cost(appliance, provider, 'Used CPU',
        average_cpu_used_in_mhz, description, 'Compute', consumed_hours)

    memory_used_cost = resource_cost(appliance, provider, 'Used Memory',
        average_memory_used_in_mb, description, 'Compute', consumed_hours)

    network_used_cost = resource_cost(appliance, provider, 'Used Network I/O',
        average_network_io, description, 'Compute', consumed_hours)

    disk_used_cost = resource_cost(appliance, provider, 'Used Disk I/O',
        average_disk_io, description, 'Compute', consumed_hours)

    storage_used_cost = resource_cost(appliance, provider, 'Used Disk Storage',
        average_storage_used, description, 'Storage', consumed_hours)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost,
            "storage_used_cost": storage_used_cost}


@pytest.fixture(scope="module")
def chargeback_report_default(appliance, vm_ownership, assign_default_rate, provider):
    # Create a Chargeback report based on the default rate; Queue the report.
    owner = vm_ownership
    data = {
        'menu_name': 'cb_' + provider.name,
        'title': 'cb_' + provider.name,
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

    logger.info('Queuing chargeback report with default rate for {} provider'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.saved_reports.all()[0].data.rows)
    report.delete()


@pytest.fixture(scope="module")
def chargeback_report_custom(appliance, vm_ownership, assign_custom_rate, provider):
    # Create a Chargeback report based on a custom rate; Queue the report
    owner = vm_ownership
    data = {
        'menu_name': 'cb_custom_' + provider.name,
        'title': 'cb_custom' + provider.name,
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

    logger.info('Queuing chargeback report with custom rate for {} provider'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.saved_reports.all()[0].data.rows)
    report.delete()


@pytest.fixture(scope="module")
def new_compute_rate():
    # Create a new Compute Chargeback rate
    try:
        desc = 'custom_' + fauxfactory.gen_alphanumeric()
        compute = rates.ComputeRate(description=desc,
                    fields={'Used CPU':
                            {'per_time': 'Hourly', 'variable_rate': '3'},
                            'Used Disk I/O':
                            {'per_time': 'Hourly', 'variable_rate': '2'},
                            'Used Memory':
                            {'per_time': 'Hourly', 'variable_rate': '2'}})
        compute.create()
        if not BZ(1532368, forced_streams=['5.9']).blocks:
            storage = rates.StorageRate(description=desc,
                    fields={'Used Disk Storage':
                            {'per_time': 'Hourly', 'variable_rate': '3'}})
            storage.create()
        yield desc
    finally:
        compute.delete()
        if not BZ(1532368, forced_streams=['5.9']).blocks:
            storage.delete()


@pytest.mark.rhv3
# Tests to validate costs reported in the Chargeback report for various metrics.
# The costs reported in the Chargeback report should be approximately equal to the
# costs estimated in the chargeback_costs_default/chargeback_costs_custom fixtures.
@pytest.mark.uncollectif(lambda provider: provider.one_of(CloudProvider))
def test_validate_default_rate_cpu_usage_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate CPU usage cost.
       Calculation is based on default Chargeback rate.
    """
    for groups in chargeback_report_default:
        if groups["CPU Used Cost"]:
            estimated_cpu_usage_cost = chargeback_costs_default['cpu_used_cost']
            cost_from_report = groups["CPU Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_cpu_usage_cost - DEVIATION <= float(cost) <= \
                estimated_cpu_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv2
@pytest.mark.uncollectif(lambda provider: provider.one_of(EC2Provider, GCEProvider))
def test_validate_default_rate_memory_usage_cost(chargeback_costs_default,
        chargeback_report_default):
    """Test to validate memory usage cost.
       Calculation is based on default Chargeback rate.

    """
    for groups in chargeback_report_default:
        if groups["Memory Used Cost"]:
            estimated_memory_usage_cost = chargeback_costs_default['memory_used_cost']
            cost_from_report = groups["Memory Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_memory_usage_cost - DEVIATION <= float(cost) <= \
                estimated_memory_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
def test_validate_default_rate_network_usage_cost(chargeback_costs_default,
        chargeback_report_default):
    """Test to validate network usage cost.
       Calculation is based on default Chargeback rate.

    """
    for groups in chargeback_report_default:
        if groups["Network I/O Used Cost"]:
            estimated_network_usage_cost = chargeback_costs_default['network_used_cost']
            cost_from_report = groups["Network I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_network_usage_cost - DEVIATION <= float(cost) <= \
                estimated_network_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
def test_validate_default_rate_disk_usage_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate disk usage cost.
       Calculation is based on default Chargeback rate.

    """
    for groups in chargeback_report_default:
        if groups["Disk I/O Used Cost"]:
            estimated_disk_usage_cost = chargeback_costs_default['disk_used_cost']
            cost_from_report = groups["Disk I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_disk_usage_cost - DEVIATION <= float(cost) <= \
                estimated_disk_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
def test_validate_default_rate_storage_usage_cost(chargeback_costs_default,
        chargeback_report_default):
    """Test to validate stoarge usage cost.
       Calculation is based on default Chargeback rate.
    """
    for groups in chargeback_report_default:
        if groups["Storage Used Cost"]:
            estimated_storage_usage_cost = chargeback_costs_default['storage_used_cost']
            cost_from_report = groups["Storage Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_storage_usage_cost - DEVIATION <= float(cost) <= \
                estimated_storage_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
@pytest.mark.uncollectif(lambda provider: provider.one_of(CloudProvider))
def test_validate_custom_rate_cpu_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate CPU usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["CPU Used Cost"]:
            estimated_cpu_usage_cost = chargeback_costs_custom['cpu_used_cost']
            cost_from_report = groups["CPU Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_cpu_usage_cost - DEVIATION <= float(cost) <= \
                estimated_cpu_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv1
@pytest.mark.uncollectif(lambda provider: provider.one_of(EC2Provider, GCEProvider))
def test_validate_custom_rate_memory_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate memory usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["Memory Used Cost"]:
            estimated_memory_usage_cost = chargeback_costs_custom['memory_used_cost']
            cost_from_report = groups["Memory Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_memory_usage_cost - DEVIATION <= float(cost) <= \
                estimated_memory_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
def test_validate_custom_rate_network_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate network usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["Network I/O Used Cost"]:
            estimated_network_usage_cost = chargeback_costs_custom['network_used_cost']
            cost_from_report = groups["Network I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_network_usage_cost - DEVIATION <= float(cost) <= \
                estimated_network_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
def test_validate_custom_rate_disk_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate disk usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["Disk I/O Used Cost"]:
            estimated_disk_usage_cost = chargeback_costs_custom['disk_used_cost']
            cost_from_report = groups["Disk I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_disk_usage_cost - DEVIATION <= float(cost) <= \
                estimated_disk_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break


@pytest.mark.rhv3
def test_validate_custom_rate_storage_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate stoarge usage cost.
       Calculation is based on custom Chargeback rate.
    """
    for groups in chargeback_report_custom:
        if groups["Storage Used Cost"]:
            estimated_storage_usage_cost = chargeback_costs_custom['storage_used_cost']
            cost_from_report = groups["Storage Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_storage_usage_cost - DEVIATION <= float(cost) <= \
                estimated_storage_usage_cost + DEVIATION, \
                'Estimated cost and report cost do not match'
            break
