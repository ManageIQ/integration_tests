# -*- coding: utf-8 -*-

import cfme.configure.access_control as ac
import cfme.intelligence.chargeback as cb
import fauxfactory
import pytest
import re

from cfme import Credential
from cfme import test_requirements
from cfme.common.vm import VM
from cfme.configure.configuration import get_server_roles, set_server_roles, candu
from cfme.intelligence.reports.reports import CustomReport
from datetime import date
from utils.log import logger
from utils import testgen, version
from utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.chargeback
]


def pytest_generate_tests(metafunc):
    # Filter out providers not meant for Chargeback Testing
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc, ['virtualcenter', 'rhevm'],
        required_fields=[(['cap_and_util', 'test_chargeback'], True)]
    )

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        capandu_data = args['provider'].data['cap_and_util']

        stream = capandu_data.get('chargeback_runs_on_stream', '')
        if not version.current_version().is_in_series(str(stream)):
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='secret')


@pytest.yield_fixture(scope="module")
def vm_ownership(enable_candu, setup_provider_modscope, provider):
    # In these tests, chargeback reports are filtered on VM owner.So,VMs have to be
    # assigned ownership.
    try:
        vm_name = provider.data['cap_and_util']['chargeback_vm']
        vm = VM.factory(vm_name, provider)

        cb_group = ac.Group(description='EvmGroup-super_administrator')
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
def enable_candu(db):

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

    candu.disable_all()
    set_server_roles(**original_roles)


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


def count_records_rollups_table(db, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    ems = db['ext_management_systems']
    provider_id = db.session.query(ems).filter(ems.name == provider.name).first().id
    rollups = db['metric_rollups']

    count = db.session.query(rollups).filter(rollups.parent_ems_id == provider_id,
        rollups.resource_name == vm_name).count()
    if count > 0:
        return count
    return 0


@pytest.fixture(scope="module")
def resource_usage(vm_ownership, db, provider, ssh_client_modscope):
    # Retrieve resource usage values from metric_rollups table.
    average_cpu_used_in_mhz = 0
    average_memory_used_in_mb = 0
    average_network_io = 0
    average_disk_io = 0
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    metrics = db['metrics']
    rollups = db['metric_rollups']
    ems = db['ext_management_systems']
    logger.info('DELETING METRICS DATA FROM METRICS AND METRIC_ROLLUPS tables')
    db.session.query(metrics).delete()
    db.session.query(rollups).delete()

    provider_id = db.session.query(ems).filter(ems.name == provider.name).first().id

    # Chargeback reporting is not done on real-time values.So, we are capturing C&U data
    # and forcing hourly rollups by running these commands through the Rails console.

    logger.info('CAPTURING PERF DATA FOR VM {} running on {}'.format(vm_name, provider.name))
    ssh_client_modscope.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_capture('realtime',1.hour.ago.utc, Time.now.utc);\
        vm.perf_rollup_range('realtime',1.hour.ago.utc, Time.now.utc)\"".
        format(provider_id, repr(vm_name)))
    wait_for(count_records_rollups_table, [db, provider], timeout=60, fail_condition=0,
        message="rollups")

    # Since we are collecting C&U data for > 1 hour, there will be multiple hourly records per VM
    # in the metric_rollups DB table.The values from these hourly records are summed up.

    with db.transaction:
        providers = (
            db.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(rollups.capture_interval_name == 'hourly', rollups.resource_name == vm_name,
            ems.name == provider.name, rollups.timestamp >= date.today())
        )
    for record in db.session.query(rollups).filter(rollups.id.in_(providers.subquery())):
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


def query_rate(db, provider, metric, description, rate_type):
    # Query the DB for Chargeback rates
    details = db['chargeback_rate_details']
    rates = db['chargeback_rates']

    with db.transaction:
        providers = (
            db.session.query(details.id)
            .join(rates, details.chargeback_rate_id == rates.id)
            .filter(details.metric == metric, rates.description == description,
                rates.rate_type == rate_type)
        )
        rate = db.session.query(details).filter(details.id.in_(
            providers.subquery())).first().rate
    return rate


@pytest.fixture(scope="module")
def chargeback_costs_default(resource_usage, db, provider):
    # Estimate Chargeback costs using default Chargeback rate and resource usage from the DB.
    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']

    cpu_rate = query_rate(db, provider, 'cpu_usagemhz_rate_average', 'Default', 'Compute')
    cpu_used_cost = average_cpu_used_in_mhz * float(cpu_rate) / 24

    memory_rate = query_rate(db, provider, 'derived_memory_used', 'Default', 'Compute')
    memory_used_cost = average_memory_used_in_mb * float(memory_rate) / 24

    network_rate = query_rate(db, provider, 'net_usage_rate_average', 'Default', 'Compute')
    network_used_cost = average_network_io * float(network_rate)

    disk_rate = query_rate(db, provider, 'disk_usage_rate_average', 'Default', 'Compute')
    disk_used_cost = average_disk_io * float(disk_rate)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost}


@pytest.fixture(scope="module")
def chargeback_costs_custom(resource_usage, new_compute_rate, db, provider):
    # Estimate Chargeback costs using custom Chargeback rate and resource usage from the DB.
    description = new_compute_rate

    average_cpu_used_in_mhz = resource_usage['average_cpu_used_in_mhz']
    average_memory_used_in_mb = resource_usage['average_memory_used_in_mb']
    average_network_io = resource_usage['average_network_io']
    average_disk_io = resource_usage['average_disk_io']

    cpu_rate = query_rate(db, provider, 'cpu_usagemhz_rate_average', description, 'Compute')
    cpu_used_cost = average_cpu_used_in_mhz * float(cpu_rate) / 24

    memory_rate = query_rate(db, provider, 'derived_memory_used', description, 'Compute')
    memory_used_cost = average_memory_used_in_mb * float(memory_rate) / 24

    network_rate = query_rate(db, provider, 'net_usage_rate_average', description, 'Compute')
    network_used_cost = average_network_io * float(network_rate)

    disk_rate = query_rate(db, provider, 'disk_usage_rate_average', description, 'Compute')
    disk_used_cost = average_disk_io * float(disk_rate)

    return {"cpu_used_cost": cpu_used_cost,
            "memory_used_cost": memory_used_cost,
            "network_used_cost": network_used_cost,
            "disk_used_cost": disk_used_cost}


@pytest.yield_fixture(scope="module")
def chargeback_report_default(vm_ownership, assign_compute_default_rate, provider):
    # Create a Chargeback report based on the default Compute rate; Queue the report
    owner = vm_ownership
    data = {'menu_name': 'cb_' + provider.name,
            'title': 'cb_' + provider.name,
            'base_report_on': 'Chargebacks',
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
            'base_report_on': 'Chargebacks',
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
    # Create a new Chargeback compute rate
    try:
        desc = 'custom_' + fauxfactory.gen_alphanumeric()
        ccb = cb.ComputeRate(description=desc,
                         cpu_used=(3, cb.DAILY),
                         disk_io=(1, cb.HOURLY),
                         compute_fixed_1=(0, cb.DAILY),
                         compute_fixed_2=(0, cb.MONTHLY),
                         mem_alloc=(0, cb.DAILY),
                         mem_used=(2, cb.DAILY),
                         net_io=(2, cb.HOURLY))
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
