# -*- coding: utf-8 -*-

import re
from datetime import date

import fauxfactory
import pytest

import cfme.configure.access_control as ac
import cfme.intelligence.chargeback as cb
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.common.vm import VM
from cfme.common.provider import BaseProvider
from cfme.configure.configuration import get_server_roles, set_server_roles, candu
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.intelligence.reports.reports import CustomReport
from fixtures.provider import setup_or_skip
from utils import testgen
from utils.blockers import BZ
from utils.log import logger
from utils.version import current_version
from utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.meta(blockers=[BZ(1433984, forced_streams=["5.7", "5.8", "upstream"])]),
    test_requirements.chargeback
]


def pytest_generate_tests(metafunc):
    # Filter out providers not meant for Chargeback Testing
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [VMwareProvider, RHEVMProvider],
        required_fields=[(['cap_and_util', 'test_chargeback'], True)]
    )

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.yield_fixture(scope="module")
def clean_setup_provider(request, provider):
    BaseProvider.clear_providers()
    setup_or_skip(request, provider)
    yield
    BaseProvider.clear_providers()


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='secret')


@pytest.yield_fixture(scope="module")
def vm_ownership(enable_candu, clean_setup_provider, provider):
    # In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    # assigned ownership.
    try:
        vm_name = provider.data['cap_and_util']['chargeback_vm']
        vm = VM.factory(vm_name, provider)

        cb_group = ac.Group(description='EvmGroup-user')
        user = ac.User(name=provider.name + fauxfactory.gen_alphanumeric(),
                credential=new_credential(),
                email='abc@example.com',
                group=cb_group,
                cost_center='Workload',
                value_assign='Database')
        user.create()
        vm.set_ownership(user=user.name)
        logger.info('ASSIGNED VM OWNERSHIP FOR {} RUNNING ON {}'.format(vm_name, provider.name))

        yield user.name
    finally:
        vm.unset_ownership()
        user.delete()


@pytest.yield_fixture(scope="module")
def enable_candu():

    # C&U data collection consumes a lot of memory and CPU.So, we are disabling some server roles
    # that are not needed for Chargeback reporting.
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

    set_server_roles(**original_roles)
    candu.disable_all()


@pytest.fixture(scope="module")
def assign_compute_default_rate(provider):
    # Assign default Compute rate to the Enterprise and then queue the Chargeback report.
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            "Enterprise": "Default"
        })
    enterprise.computeassign()
    logger.info('ASSIGNING DEFAULT COMPUTE RATE')


@pytest.yield_fixture(scope="module")
def assign_compute_custom_rate(new_compute_rate, provider):
    # Assign custom Compute rate to the Enterprise and then queue the Chargeback report.
    description = new_compute_rate
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            "Enterprise": description
        })
    enterprise.computeassign()
    logger.info('ASSIGNING CUSTOM COMPUTE RATE')

    yield

    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            "Enterprise": "Default"
        })
    enterprise.computeassign()


def count_records_rollups_table(appliance, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    ems = appliance.db['ext_management_systems']
    provider_id = appliance.db.session.query(ems).filter(ems.name == provider.name).first().id
    rollups = appliance.db['metric_rollups']

    count = appliance.db.session.query(rollups).filter(rollups.parent_ems_id == provider_id,
        rollups.resource_name == vm_name).count()
    if count > 0:
        return count
    return 0


@pytest.fixture(scope="module")
def resource_usage(vm_ownership, appliance, provider):
    # Retrieve resource usage values from metric_rollups table.
    average_cpu_used_in_mhz = 0
    average_memory_used_in_mb = 0
    average_network_io = 0
    average_disk_io = 0
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    metrics = appliance.db['metrics']
    rollups = appliance.db['metric_rollups']
    ems = appliance.db['ext_management_systems']
    logger.info('DELETING METRICS DATA FROM METRICS AND METRIC_ROLLUPS TABLES')
    appliance.db.session.query(metrics).delete()
    appliance.db.session.query(rollups).delete()

    provider_id = appliance.db.session.query(ems).filter(ems.name == provider.name).first().id

    # Chargeback reporting is done on rollups and not  real-time values.So, we are capturing C&U
    # data and forcing hourly rollups by running these commands through the Rails console.

    command = ('Metric::Targets.perf_capture_always = {:storage=>true, :host_and_cluster=>true};')
    appliance.ssh_client.run_rails_command(command, timeout=None)

    logger.info('CAPTURING PERF DATA FOR VM {} running on {}'.format(vm_name, provider.name))
    appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_capture('realtime',1.hour.ago.utc, Time.now.utc);\
        vm.perf_rollup_range('realtime',1.hour.ago.utc, Time.now.utc)\"".
        format(provider_id, repr(vm_name)))

    # New C&U data may sneak in since 1)C&U server roles are running and 2)collection for clusters
    # and hosts is on.This would mess up our Chargeback calculations, so we are disabling C&U
    # collection after data has been fetched for the last hour.
    command = ('Metric::Targets.perf_capture_always = {:storage=>false, :host_and_cluster=>false};')
    appliance.ssh_client.run_rails_command(command, timeout=None)

    wait_for(count_records_rollups_table, [appliance, provider], timeout=120, fail_condition=0,
        message="rollups")

    # Since we are collecting C&U data for > 1 hour, there will be multiple hourly records per VM
    # in the metric_rollups DB table.The values from these hourly records are summed up.

    with appliance.db.transaction:
        providers = (
            appliance.db.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(rollups.capture_interval_name == 'hourly', rollups.resource_name == vm_name,
            ems.name == provider.name, rollups.timestamp >= date.today())
        )

    for record in appliance.db.session.query(rollups).filter(rollups.id.in_(providers.subquery())):
        if record.cpu_usagemhz_rate_average is None:
            pass
        else:
            average_cpu_used_in_mhz = average_cpu_used_in_mhz + record.cpu_usagemhz_rate_average
            average_memory_used_in_mb = average_memory_used_in_mb + record.derived_memory_used
            average_network_io = average_network_io + record.net_usage_rate_average
            average_disk_io = average_disk_io + record.disk_usage_rate_average

    return {"average_cpu_used_in_mhz": average_cpu_used_in_mhz,
            "average_memory_used_in_mb": average_memory_used_in_mb,
            "average_network_io": average_network_io,
            "average_disk_io": average_disk_io}


def query_rate(appliance, provider, metric, description, rate_type):
    # Query the DB for Chargeback rates
    tiers = appliance.db['chargeback_tiers']
    details = appliance.db['chargeback_rate_details']
    rates = appliance.db['chargeback_rates']

    with appliance.db.transaction:
        providers = (
            appliance.db.session.query(tiers.variable_rate).
            join(details, tiers.chargeback_rate_detail_id == details.id).
            join(rates, details.chargeback_rate_id == rates.id).
            filter(details.metric == metric).
            filter(rates.rate_type == rate_type).
            filter(rates.description == description)
        )
    rate = appliance.db.session.query(tiers).filter(tiers.variable_rate.in_(
        providers.subquery())).first().variable_rate
    return rate


@pytest.fixture(scope="module")
def chargeback_costs_default(resource_usage, appliance, provider):
    # Estimate Chargeback costs using default Chargeback rate and resource usage from the DB.
    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']

    cpu_rate = query_rate(appliance, provider, 'cpu_usagemhz_rate_average', 'Default', 'Compute')
    cpu_used_cost = average_cpu_used_in_mhz * float(cpu_rate)

    memory_rate = query_rate(appliance, provider, 'derived_memory_used', 'Default', 'Compute')
    memory_used_cost = average_memory_used_in_mb * float(memory_rate)

    network_rate = query_rate(appliance, provider, 'net_usage_rate_average', 'Default', 'Compute')
    network_used_cost = average_network_io * float(network_rate)

    disk_rate = query_rate(appliance, provider, 'disk_usage_rate_average', 'Default', 'Compute')
    disk_used_cost = average_disk_io * float(disk_rate)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost}


@pytest.fixture(scope="module")
def chargeback_costs_custom(resource_usage, new_compute_rate, appliance, provider):
    # Estimate Chargeback costs using custom Chargeback rate and resource usage from the DB.
    description = new_compute_rate

    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']

    cpu_rate = query_rate(appliance, provider, 'cpu_usagemhz_rate_average', description, 'Compute')
    cpu_used_cost = average_cpu_used_in_mhz * float(cpu_rate)

    memory_rate = query_rate(appliance, provider, 'derived_memory_used', description, 'Compute')
    memory_used_cost = average_memory_used_in_mb * float(memory_rate)

    network_rate = query_rate(appliance, provider, 'net_usage_rate_average', description, 'Compute')
    network_used_cost = average_network_io * float(network_rate)

    disk_rate = query_rate(appliance, provider, 'disk_usage_rate_average', description, 'Compute')
    disk_used_cost = average_disk_io * float(disk_rate)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost}


@pytest.yield_fixture(scope="module")
def chargeback_report_default(vm_ownership, assign_compute_default_rate, provider):
    # Create a Chargeback report based on the default Compute rate; Queue the report.
    owner = vm_ownership
    data = {'menu_name': 'cb_' + provider.name,
            'title': 'cb_' + provider.name,
            'base_report_on': 'Chargeback for Vms',
            'report_fields': ['Memory Used', 'Memory Used Cost', 'Owner',
            'CPU Used', 'CPU Used Cost',
            'Disk I/O Used', 'Disk I/O Used Cost',
            'Network I/O Used', 'Network I/O Used Cost'],
            'filter_show_costs': 'Owner',
            'filter_owner': owner,
            'interval_end': 'Today (partial)'}
    report = CustomReport(is_candu=True, **data)
    report.create()

    logger.info('QUEUING DEFAULT CHARGEBACK REPORT FOR {} PROVIDER'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.get_saved_reports()[0].data[0].rows)
    report.delete()


@pytest.yield_fixture(scope="module")
def chargeback_report_custom(vm_ownership, assign_compute_custom_rate, provider):
    # Create a Chargeback report based on a custom Compute rate; Queue the report
    owner = vm_ownership
    data = {'menu_name': 'cb_custom_' + provider.name,
            'title': 'cb_custom' + provider.name,
            'base_report_on': 'Chargeback for Vms',
            'report_fields': ['Memory Used', 'Memory Used Cost', 'Owner',
            'CPU Used', 'CPU Used Cost',
            'Disk I/O Used', 'Disk I/O Used Cost',
            'Network I/O Used', 'Network I/O Used Cost'],
            'filter_show_costs': 'Owner',
            'filter_owner': owner,
            'interval_end': 'Today (partial)'}
    report = CustomReport(is_candu=True, **data)
    report.create()

    logger.info('QUEUING CUSTOM CHARGEBACK REPORT FOR {} PROVIDER'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.get_saved_reports()[0].data[0].rows)
    report.delete()


@pytest.yield_fixture(scope="module")
def new_compute_rate():
    # Create a new Compute Chargeback rate
    try:
        desc = 'custom_' + fauxfactory.gen_alphanumeric()
        ccb = cb.ComputeRate(description=desc,
                    fields={'Used CPU':
                            {'per_time': 'Hourly', 'variable_rate': '3'},
                            'Used Disk I/O':
                            {'per_time': 'Hourly', 'variable_rate': '2'},
                            'Used Memory':
                            {'per_time': 'Hourly', 'variable_rate': '2'}})
        ccb.create()
        yield desc
    finally:
        ccb.delete()


# Tests to validate costs reported in the Chargeback report for various metrics.
# The costs reported in the Chargeback report should be approximately equal to the
# costs estimated in the chargeback_costs_default/chargeback_costs_custom fixtures.
def test_validate_default_rate_cpu_usage_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate CPU usage cost.
       Calculation is based on default Chargeback rate.
    """
    for groups in chargeback_report_default:
        if groups["CPU Used Cost"]:
            estimated_cpu_usage_cost = chargeback_costs_default['cpu_used_cost']
            cost_from_report = groups["CPU Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_cpu_usage_cost - 1.0 <= float(cost) \
                <= estimated_cpu_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


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
            assert estimated_memory_usage_cost - 1.0 <= float(cost) \
                <= estimated_memory_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


@pytest.mark.uncollectif(
    lambda provider: current_version() > "5.5")
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
            assert estimated_network_usage_cost - 1.0 <= float(cost) \
                <= estimated_network_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_default_rate_disk_usage_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate disk usage cost.
       Calculation is based on default Chargeback rate.

    """
    for groups in chargeback_report_default:
        if groups["Disk I/O Used Cost"]:
            estimated_disk_usage_cost = chargeback_costs_default['disk_used_cost']
            cost_from_report = groups["Disk I/O Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_disk_usage_cost - 1.0 <= float(cost) \
                <= estimated_disk_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_custom_rate_cpu_usage_cost(chargeback_costs_custom, chargeback_report_custom):
    """Test to validate CPU usage cost.
       Calculation is based on custom Chargeback rate.

    """
    for groups in chargeback_report_custom:
        if groups["CPU Used Cost"]:
            estimated_cpu_usage_cost = chargeback_costs_custom['cpu_used_cost']
            cost_from_report = groups["CPU Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_cpu_usage_cost - 1.0 <= float(cost) \
                <= estimated_cpu_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_custom_rate_memory_usage_cost(chargeback_costs_custom, chargeback_report_custom):
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


@pytest.mark.uncollectif(
    lambda provider: current_version() > "5.5")
def test_validate_custom_rate_network_usage_cost(chargeback_costs_custom, chargeback_report_custom):
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


def test_validate_custom_rate_disk_usage_cost(chargeback_costs_custom, chargeback_report_custom):
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
