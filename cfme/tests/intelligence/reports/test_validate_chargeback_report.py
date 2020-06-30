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
import re
from datetime import date

import fauxfactory
import pytest
from wrapanapi import VmState

import cfme.intelligence.chargeback.assignments as cb
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for


cloud_and_infra = ProviderFilter(classes=[CloudProvider, InfraProvider],
                                 required_fields=[(['cap_and_util', 'test_chargeback'], True)])
not_scvmm = ProviderFilter(classes=[SCVMMProvider], inverted=True)  # SCVMM doesn't support C&U
not_cloud = ProviderFilter(classes=[CloudProvider], inverted=True)
not_ec2_gce = ProviderFilter(classes=[GCEProvider, EC2Provider], inverted=True)


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers, filters=[cloud_and_infra, not_scvmm], scope='module'),
    pytest.mark.usefixtures('has_no_providers_modscope', 'setup_provider_modscope'),
    test_requirements.chargeback,
    pytest.mark.meta(blockers=[BZ(1843942, forced_streams=['5.11'],
        unblock=lambda provider: not provider.one_of(AzureProvider))])
]

# Allowed deviation between the reported value in the Chargeback report and the estimated value.
DEV = 1


def cost_comparison(estimate, expected):
    subbed = re.sub(r'[$,]', r'', expected)
    return float(estimate - DEV) <= float(subbed) <= float(estimate + DEV)


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
    # TODO Move this to a global fixture
    for klass in (cb.ComputeAssign, cb.StorageAssign):
        enterprise = klass(
            assign_to="The Enterprise",
            selections={
                'Enterprise': {'Rate': 'Default'}
            })
        enterprise.assign()
    logger.info('Assigning DEFAULT Compute rate')

    yield

    # Resetting the Chargeback rate assignment
    for klass in (cb.ComputeAssign, cb.StorageAssign):
        enterprise = klass(
            assign_to="The Enterprise",
            selections={
                'Enterprise': {'Rate': '<Nothing>'}
            })
        enterprise.assign()


@pytest.fixture(scope="module")
def assign_custom_rate(new_compute_rate, provider):
    # Assign custom Compute rate to the Enterprise and then queue the Chargeback report.
    # TODO Move this to a global fixture
    description = new_compute_rate
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
        assert result.success, f"Failed to capture VM C&U data:"

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
    assert result.success, f"Failed to rollup VM C&U data:"

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

    yield dict(
        average_cpu_used_in_mhz=average_cpu_used_in_mhz,
        average_memory_used_in_mb=average_memory_used_in_mb,
        average_network_io=average_network_io,
        average_disk_io=average_disk_io,
        average_storage_used=average_storage_used,
        consumed_hours=consumed_hours
    )
    appliance.server.settings.enable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector')


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

    logger.info(f'Queuing chargeback report with default rate for {provider.name} provider')
    report.queue(wait_for_finish=True)

    yield list(report.saved_reports.all()[0].data.rows)

    if report.exists:
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

    logger.info(f'Queuing chargeback report with custom rate for {provider.name} provider')
    report.queue(wait_for_finish=True)

    yield list(report.saved_reports.all()[0].data.rows)

    if report.exists:
        report.delete()


@pytest.fixture(scope="module")
def new_compute_rate(appliance):
    # Create a new Compute Chargeback rate
    try:
        desc = 'cstm_' + fauxfactory.gen_alphanumeric()
        compute = appliance.collections.compute_rates.create(
            description=desc,
            fields={
                'Used CPU': {'per_time': 'Hourly', 'variable_rate': '3'},
                'Used Disk I/O': {'per_time': 'Hourly', 'variable_rate': '2'},
                'Used Memory': {'per_time': 'Hourly', 'variable_rate': '2'}
            }
        )
        storage = appliance.collections.storage_rates.create(
            description=desc,
            fields={
                'Used Disk Storage': {'per_time': 'Hourly', 'variable_rate': '3'}
            }
        )
    except Exception as ex:
        pytest.fail(
            'Exception while creating compute/storage rates for chargeback report tests. {}'
            .format(ex)
        )

    yield desc

    for entity in [compute, storage]:
        try:
            entity.delete_if_exists()
        except Exception as ex:
            pytest.fail(
                'Exception while cleaning up compute/storage rates for chargeback report tests. {}'
                .format(ex)
            )


# Tests to validate costs reported in the Chargeback report for various metrics.
# The costs reported in the Chargeback report should be approximately equal to the
# costs estimated in the chargeback_costs_default/chargeback_costs_custom fixtures.
@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_cloud],
                      scope='module')
def test_validate_default_rate_cpu_usage_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate CPU usage cost.
       Calculation is based on default Chargeback rate.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_default:
        if groups["CPU Used Cost"]:
            est_cpu_cost = chargeback_costs_default['cpu_used_cost']
            report_cost = groups["CPU Used Cost"]

            assert cost_comparison(est_cpu_cost, report_cost), 'CPU report costs does not match'
            break


@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_ec2_gce],
                      scope='module')
def test_validate_default_rate_memory_usage_cost(chargeback_costs_default,
        chargeback_report_default):
    """Test to validate memory usage cost.
       Calculation is based on default Chargeback rate.


    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_default:
        if groups["Memory Used Cost"]:
            est_memory_cost = chargeback_costs_default['memory_used_cost']
            report_cost = groups["Memory Used Cost"]
            assert cost_comparison(est_memory_cost, report_cost), 'Memory report cost do not match'
            break


def test_validate_default_rate_network_usage_cost(chargeback_costs_default,
        chargeback_report_default):
    """Test to validate network usage cost.
       Calculation is based on default Chargeback rate.


    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_default:
        if groups["Network I/O Used Cost"]:
            est_net_cost = chargeback_costs_default['network_used_cost']
            report_cost = groups["Network I/O Used Cost"]
            assert cost_comparison(est_net_cost, report_cost), 'Network report cost does not match'
            break


def test_validate_default_rate_disk_usage_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate disk usage cost.
       Calculation is based on default Chargeback rate.


    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_default:
        if groups["Disk I/O Used Cost"]:
            est_disk_cost = chargeback_costs_default['disk_used_cost']
            report_cost = groups["Disk I/O Used Cost"]
            assert cost_comparison(est_disk_cost, report_cost), 'Disk report cost does not match'
            break


def test_validate_default_rate_storage_usage_cost(chargeback_costs_default,
        chargeback_report_default):
    """Test to validate stoarge usage cost.
       Calculation is based on default Chargeback rate.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/12h
        casecomponent: Reporting
    """
    for groups in chargeback_report_default:
        if groups["Storage Used Cost"]:
            est_stor_cost = chargeback_costs_default['storage_used_cost']
            report_cost = groups["Storage Used Cost"]
            assert cost_comparison(est_stor_cost, report_cost), 'Storage report cost does not match'
            break


@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_cloud],
                      scope='module')
def test_validate_custom_rate_cpu_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate CPU usage cost.
       Calculation is based on custom Chargeback rate.


    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_custom:
        if groups["CPU Used Cost"]:
            est_cpu_cost = chargeback_costs_custom['cpu_used_cost']
            report_cost = groups["CPU Used Cost"]
            assert cost_comparison(est_cpu_cost, report_cost), 'CPU report cost does not match'
            break


@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_ec2_gce],
                      scope='module')
def test_validate_custom_rate_memory_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate memory usage cost.
       Calculation is based on custom Chargeback rate.


    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_custom:
        if groups["Memory Used Cost"]:
            est_mem_cost = chargeback_costs_custom['memory_used_cost']
            report_cost = groups["Memory Used Cost"]
            assert cost_comparison(est_mem_cost, report_cost), 'Memory report cost does not match'
            break


def test_validate_custom_rate_network_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate network usage cost.
       Calculation is based on custom Chargeback rate.


    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_custom:
        if groups["Network I/O Used Cost"]:
            est_net_cost = chargeback_costs_custom['network_used_cost']
            report_cost = groups["Network I/O Used Cost"]
            assert cost_comparison(est_net_cost, report_cost), 'Network report cost does not match'
            break


def test_validate_custom_rate_disk_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate disk usage cost.
       Calculation is based on custom Chargeback rate.


    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        initialEstimate: 1/4h
    """
    for groups in chargeback_report_custom:
        if groups["Disk I/O Used Cost"]:
            est_disk_cost = chargeback_costs_custom['disk_used_cost']
            report_cost = groups["Disk I/O Used Cost"]
            assert cost_comparison(est_disk_cost, report_cost), 'Disk report cost does not match'
            break


def test_validate_custom_rate_storage_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate stoarge usage cost.
       Calculation is based on custom Chargeback rate.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    for groups in chargeback_report_custom:
        if groups["Storage Used Cost"]:
            est_stor_cost = chargeback_costs_custom['storage_used_cost']
            report_cost = groups["Storage Used Cost"]
            assert cost_comparison(est_stor_cost, report_cost), 'Storage report cost does not match'
            break
