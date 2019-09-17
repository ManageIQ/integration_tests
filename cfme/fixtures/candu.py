"""Fixtures for Capacity and Utilization"""
import re
from collections import namedtuple
from datetime import date
from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest
from wrapanapi import VmState

from cfme.base.credential import Credential
from cfme.intelligence.chargeback.assignments import ComputeAssign
from cfme.intelligence.chargeback.assignments import StorageAssign
from cfme.utils import conf
from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient
from cfme.utils.units import Unit
from cfme.utils.wait import wait_for


# Retrieve resource usage values from metric_rollups table.
# Chargeback and metering reports are done on hourly and daily rollups, not realtime values.
# We capture C&U data and force hourly rollups by running these commands through
# the Rails console.
#
# Metering reports differ from chargeback reports in that metering reports:
#   1.) report only resource usage, not costs
#   2.) report the sum total of resource usage instead of average usage.

TIME_DIVISORS = {
    'hourly': 1,
    'daily': 24,
    'weekly': 24 * 7,
    'monthly': 24 * 30,
    'yearly': 24 * 365,
}

UNITS = {
    'bytes': 'B',
    'kilobytes': 'KB',
    'megabytes': 'MB',
    'gigabytes': 'GB',
    'terabytes': 'TB',
    'hertz': 'Hz',
    'kilohertz': 'KHz',
    'megahertz': 'MHz',
    'gigahertz': 'GHz',
    'terahertz': 'THz',
    'bps': 'Bps',
    'kbps': 'KBps',
    'mbps': 'MBps',
    'gbps': 'GBps',
}

RATE_FIELDS = (
    ('rate_type', ),
    ('description', 'per_time', 'per_unit'),
    ('variable_rate', 'fixed_rate', 'start', 'finish'),
)

Resource = namedtuple('Resource', ['name', 'cost_name', 'db_column', 'db_description',
    'report_column', 'cost_report_column', 'rate_type', 'db_unit'])
RESOURCES = [
    Resource('cpu_used', 'cpu_used_cost', 'cpu_usagemhz_rate_average', 'Used CPU', 'CPU Used',
        'CPU Used Cost', 'Compute', 'MHz'),
    Resource('memory_used', 'memory_used_cost', 'derived_memory_used', 'Used Memory', 'Memory Used',
        'Memory Used Cost', 'Compute', 'MB'),
    Resource('net_used', 'net_used_cost', 'net_usage_rate_average', 'Used Network I/O',
        'Network I/O Used', 'Network I/O Used Cost', 'Compute', 'KBps'),
    Resource('disk_used', 'disk_used_cost', 'disk_usage_rate_average', 'Used Disk I/O',
        'Disk I/O Used', 'Disk I/O Used Cost', 'Compute', 'KBps'),
    Resource('storage_used', 'storage_used_cost', 'derived_vm_used_disk_storage',
        'Used Disk Storage', 'Storage Used', 'Storage Used Cost', 'Storage', 'B'),
    Resource('cpu_alloc', 'cpu_alloc_cost', 'derived_vm_numvcpus', 'Allocated CPU Count',
        'vCPUs Allocated over Time Period', 'vCPUs Allocated Cost', 'Compute', ''),
    Resource('memory_alloc', 'memory_alloc_cost', 'derived_memory_available', 'Allocated Memory',
        'Memory Allocated over Time Period', 'Memory Allocated Cost', 'Compute', 'MB'),
    Resource('storage_alloc', 'storage_alloc_cost', 'derived_vm_allocated_disk_storage',
        'Allocated Disk Storage', 'Storage Allocated', 'Storage Allocated Cost', 'Storage', 'B'),
]


def calculate_cost(resource, total, chargeback_rate_tiers):
    """Find the matching rate tier for the given resource and resource total, then calculate
    and return the chargeback cost."""
    for tier in chargeback_rate_tiers:
        if tier['description'] != resource.db_description:
            continue

        time_units = total['count'] / TIME_DIVISORS[tier['per_time']]
        resource_value = float(total['sum']) / time_units if (
            'Used' in tier['description']) else float(total['max'])
        # Convert the resource to the unit in the rate tier's per_unit field.
        if tier['per_unit'] in UNITS:
            resource_value /= float(Unit.parse(f"1 {UNITS[tier['per_unit']]}"))
        fixed = total['fixed']
        if tier['start'] <= resource_value < tier['finish']:
            return round(tier['variable_rate'] * resource_value * time_units
                + tier['fixed_rate'] * fixed, 2)

    pytest.fail(f"Failed to match chargeback tier.")


@pytest.fixture(scope="module")
def enable_candu(appliance):
    """C&U data collection consumes a lot of memory and CPU.
    Disable server roles that are not needed for candu / chargeback / metering report tests."""
    candu = appliance.collections.candus
    server_settings = appliance.server.settings
    original_roles = server_settings.server_roles_db
    enabled_roles = ('ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    disabled_roles = ('automate', 'smartstate')

    server_settings.enable_server_roles(*enabled_roles)
    server_settings.disable_server_roles(*disabled_roles)
    candu.enable_all()

    yield

    candu.disable_all()
    server_settings.update_server_roles_db(original_roles)


@pytest.fixture(scope="module")
def collect_data(appliance, provider, interval='hourly', back='7.days'):
    """Collect hourly back data for vsphere provider"""
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    # Capture real-time C&U data
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_capture({}, {}.ago.utc, Time.now.utc)\""
        .format(provider.id, repr(vm_name), repr(interval), back))
    return ret.success


@pytest.fixture(scope="module")
def enable_candu_category(appliance):
    """Enable capture C&U Data for tag category location by navigating to the Configuration ->
       Region page. Click 'Tags' tab , select required company category under
       'My Company Categories' and enable 'Capture C & U Data' for the category.
    """
    collection = appliance.collections.categories
    location_category = collection.instantiate(name="location", display_name="Location")
    if not location_category.capture_candu:
        location_category.update(updates={"capture_candu": True})
    return location_category


@pytest.fixture(scope="function")
def candu_tag_vm(provider, enable_candu_category):
    """Add location tag to VM if not available"""
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate('cu-24x7', provider)
    tag = enable_candu_category.collections.tags.instantiate(name="london", display_name="London")
    vm.add_tag(tag, exists_check=True)
    return vm


@pytest.fixture(scope="module")
def candu_db_restore(temp_appliance_extended_db):
    app = temp_appliance_extended_db
    # get DB backup file
    db_storage_hostname = conf.cfme_data.bottlenecks.hostname
    db_storage_ssh = SSHClient(hostname=db_storage_hostname, **conf.credentials.bottlenecks)
    rand_filename = f"/tmp/db.backup_{fauxfactory.gen_alphanumeric()}"
    db_storage_ssh.get_file("{}/candu.db.backup".format(
        conf.cfme_data.bottlenecks.backup_path), rand_filename)
    app.ssh_client.put_file(rand_filename, "/tmp/evm_db.backup")

    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    app.db.restore()
    # When you load a database from an older version of the application, you always need to
    # run migrations.
    # https://bugzilla.redhat.com/show_bug.cgi?id=1643250
    app.db.migrate()
    app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    app.evmserverd.start()
    app.wait_for_web_ui()


@pytest.fixture(scope="module")
def chargeback_vm(appliance, provider):
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    vm = appliance.provider_based_collection(provider, coll_type='vms').instantiate(vm_name,
        provider)
    if not vm.exists_on_provider:
        pytest.skip(f"VM {vm_name!r} does not exist on provider {provider.name!r}.")
    vm.mgmt.ensure_state(VmState.RUNNING)
    yield vm


@pytest.fixture(scope="module")
def chargeback_user(appliance, chargeback_vm, provider):
    group_collection = appliance.collections.groups
    group = group_collection.instantiate(description='EvmGroup-user')

    user = None
    try:
        name_len = len(provider.name) + 10
        user = appliance.collections.users.create(
            name=fauxfactory.gen_alphanumeric(name_len, provider.name, '_'),
            credential=Credential(principal=fauxfactory.gen_alphanumeric(start='uid'),
                secret='secret'),
            email=fauxfactory.gen_email(),
            groups=group,
            cost_center='Workload',
            value_assign='Database')
        yield user
    finally:
        if user:
            user.delete()


@pytest.fixture(scope="module")
def assign_chargeback_user(chargeback_vm, chargeback_user):
    chargeback_vm.set_ownership(user=chargeback_user)
    logger.info(f"Assigned owner {chargeback_user.name!r} to VM {chargeback_vm.name!r}.")
    yield chargeback_user

    chargeback_vm.unset_ownership()
    logger.info(f"Unassigned owner from VM {chargeback_vm.name!r}.")


@pytest.fixture(scope="module")
def chargeback_rates(appliance, request):
    rate_type = getattr(request, 'param', 'default')
    # import pdb
    # pdb.set_trace()
    description = None
    if rate_type == 'default':
        description = 'Default'
        # compute = appliance.collections.compute_rates.instantiate(description='Default')
        # storage = appliance.collections.storage_rates.instantiate(description='Default')
    elif rate_type in ('hourly', 'daily', 'weekly', 'monthly'):
        try:
            desc_len = len(request.param) + 10
            description = fauxfactory.gen_alphanumeric(desc_len, request.param, '_')
            per_time = rate_type
            rate_fill = {
                'per_time': per_time.capitalize(),
                'variable_rate': str(3 * TIME_DIVISORS[per_time])
            }
            compute = appliance.collections.compute_rates.create(
                description=description,
                fields={
                    'Used CPU': rate_fill,
                    'Used Disk I/O': rate_fill,
                    'Used Memory': rate_fill,
                    'Allocated CPU Count': rate_fill,
                    'Allocated Memory': rate_fill
                }
            )
            storage = appliance.collections.storage_rates.create(
                description=description,
                fields={
                    'Used Disk Storage': rate_fill,
                    'Allocated Disk Storage': rate_fill
                }
            )
        except Exception as ex:
            pytest.fail(f"Exception while creating chargeback rates: {ex}")
    else:
        pytest.fail(f"Invalid parameter {rate_type!r} passed to chargeback_rates fixture.")

    # yield (compute, storage)
    yield description

    if rate_type != 'default':
        for rate in (compute, storage):
            try:
                rate.delete_if_exists()
            except Exception as ex:
                pytest.fail(f"Exception while deleting chargeback rates: {ex}")


@pytest.fixture(scope="module")
def assign_rates(chargeback_rates):
    """Assign chargeback rates to the Enterprise."""
    # description = chargeback_rates[0].description
    description = chargeback_rates
    for cls in (ComputeAssign, StorageAssign):
        cls(
            assign_to='The Enterprise',
            selections={
                'Enterprise': {'Rate': description}
            }).assign()
    logger.info(f"Assigned chargeback rates {description!r} to Enterprise.")

    yield chargeback_rates

    # Reset the chargeback rate assignments.
    for cls in (ComputeAssign, StorageAssign):
        cls(
            assign_to='The Enterprise',
            selections={
                'Enterprise': {'Rate': '<Nothing>'}
            }).assign()
    logger.info("Unassigned chargeback rates.")


def verify_metrics(appliance, provider, table_name, expected_count):
    """Verify that metrics are present in the metrics or metric_rollups tables."""
    interval_name = 'realtime' if table_name == 'metrics' else 'hourly'
    vm_name = provider.data['cap_and_util']['chargeback_vm']
    db_client = appliance.db.client
    ems = db_client['ext_management_systems']
    metric_table = db_client[table_name]

    with db_client.transaction:
        metric_count = (
            db_client.session.query(metric_table.id)
            .join(ems, metric_table.parent_ems_id == ems.id)
            .filter(metric_table.capture_interval_name == interval_name,
                metric_table.resource_name == vm_name,
                ems.name == provider.name,
                metric_table.timestamp >= date.today() - timedelta(days=1))
            .count()
        )

    return metric_count >= expected_count


@pytest.fixture(scope="module")
def hourly_rollups(appliance, provider, chargeback_vm):
    """Capture realtime metrics for chargeback VM, create hourly metric rollups, and then return
    a :py:class:`list` of :py:class:`dict` containing resource usage and allocation values, one for
    each rollup record:

    [{'timestamp': '01/01/2020 00:00:00', 'cpu_used': 2, 'memory_used': ..., },
     {'timestamp': '01/01/2020 01:00:00', 'cpu_used': 2, 'memory_used': ..., },
    ]

    C&U-related server roles are enabled prior to metrics collection, and the default server roles
    are restored during fixture teardown.
    """
    rollups = []
    RAILS_CMD_FMT = ('"vm = Vm.where(:ems_id => {}).where(:name => {})[0];'
        'start_time = 24.hour.ago.beginning_of_day.utc.change(:sec => 0);'
        'end_time = Time.now.utc.change(:sec => 0);'
        '{}"')

    db_client = appliance.db.client
    metrics = db_client['metrics']
    metric_rollups = db_client['metric_rollups']
    perf_states = db_client['vim_performance_states']
    ems = db_client['ext_management_systems']

    candu = appliance.collections.candus
    server_settings = appliance.server.settings
    original_roles = server_settings.server_roles_db
    enabled_roles = ('ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    disabled_roles = ('automate', 'smartstate')
    collector_roles = ('ems_metrics_collector', )

    server_settings.enable_server_roles(*enabled_roles)
    server_settings.disable_server_roles(*disabled_roles)
    candu.enable_all()

    logger.info("Deleting all rows from metrics, metric_rollups, vim_performance_states tables.")
    with db_client.transaction:
        db_client.session.query(metrics).delete()
        db_client.session.query(metric_rollups).delete()
        db_client.session.query(perf_states).delete()

    logger.info(f"Capturing realtime metrics for VM {chargeback_vm.name!r}.")
    result = appliance.ssh_client.run_rails_command(
        RAILS_CMD_FMT.format(provider.id, repr(chargeback_vm.name),
            "vm.perf_capture('realtime', start_time, end_time)"))
    assert result.success, f"Failed to capture VM realtime metrics: {result.output}"

    # TODO: update if non-UTC chargeback reports are implemented.
    expected_hours = datetime.utcnow().hour - 1 + 24
    wait_for(verify_metrics, [appliance, provider, 'metrics', 3 * expected_hours], timeout=600,
        fail_condition=False, message="Waiting for VM realtime data")

    # Disable C&U collection after fetching data, so that the server doesn't automatically collect
    # additional C&U data and mess with our reports.
    server_settings.disable_server_roles(*collector_roles)

    logger.info(f"Creating hourly metric rollups for VM {chargeback_vm.name!r}.")
    result = appliance.ssh_client.run_rails_command(
        RAILS_CMD_FMT.format(provider.id, repr(chargeback_vm.name),
            "vm.perf_rollup_range(start_time, end_time, 'realtime')"))
    assert result.success, f"Failed to rollup VM C&U data: {result.output}"

    wait_for(verify_metrics, [appliance, provider, 'metric_rollups', expected_hours], timeout=600,
        fail_condition=False, message="Waiting for hourly rollups")

    logger.info(f"Querying database for hourly rollup values for VM {chargeback_vm.name!r}.")
    state_changed_on = chargeback_vm.rest_api_entity.state_changed_on.replace(tzinfo=None)
    with db_client.transaction:
        rollup_subq = (
            db_client.session.query(metric_rollups.id)
            .join(ems, metric_rollups.parent_ems_id == ems.id)
            .filter(metric_rollups.capture_interval_name == 'hourly',
                 metric_rollups.resource_name == chargeback_vm.name,
                 ems.name == provider.name,
                 metric_rollups.timestamp >= datetime.utcnow().date() - timedelta(days=1),
                 metric_rollups.timestamp < datetime.utcnow() - timedelta(hours=1))
            .subquery()
        )

        for record in db_client.session.query(metric_rollups).filter(
                metric_rollups.id.in_(rollup_subq)):
            rollup = {'timestamp': record.timestamp}
            rollup['fixed'] = 1 if record.timestamp >= state_changed_on else 0
            for resource in RESOURCES:
                # If the value is blank/None in the db, store it as 0.
                val = getattr(record, resource.db_column) or 0
                rollup[resource.name] = Unit.parse(f'{val}{resource.db_unit}')

            rollups.append(rollup)

    logger.info(f"hourly_rollups = {rollups}")

    yield rollups

    candu.disable_all()
    server_settings.update_server_roles_db(original_roles)


@pytest.fixture(scope="module")
def resource_totals(hourly_rollups):
    """Calculate the sum of resource values and the maximum or average of resource allocation
    values, for each day.

    Returns: :py:class:`dict` of the form:

    {'cpu_used': {'MM/DD/YYYY': X, ... },
     'net_used': {'MM/DD/YYYY': Y, ... },
    }
    """
    totals = {}
    for resource in RESOURCES:
        total = totals[resource.name] = {}
        for rollup in hourly_rollups:
            date = rollup['timestamp'].strftime('%m/%d/%Y')
            if date not in total:
                sum_val = Unit.parse(f'0{resource.db_unit}')
                max_val = Unit.parse(f'0{resource.db_unit}')
                total[date] = {'sum': sum_val, 'max': max_val, 'fixed': 0, 'count': 0}
            total[date]['sum'].number += rollup[resource.name].number
            total[date]['max'].number = max(total[date]['max'].number, rollup[resource.name].number)
            total[date]['fixed'] += rollup['fixed']
            total[date]['count'] += 1
    yield totals


@pytest.fixture(scope="module")
def resource_totals_parsed(resource_totals):
    parsed_totals = {}
    for resource in RESOURCES:
        parsed_totals[resource.name] = {}
        for ts, vals in resource_totals[resource.name].items():
            avg_val = round(vals['sum'].number / vals['count'], 2)
            parsed_totals[resource.name][ts] = Unit.parse(f'{avg_val}{resource.db_unit}')
    logger.info(f"resource_totals_parsed = {parsed_totals}")
    return parsed_totals


@pytest.fixture(scope="module")
def chargeback_rate_tiers(appliance, chargeback_rates):
    """Query the DB for chargeback rate tiers.
    TODO: update rate collection class so that we can get rate/tier information
    directly via instantiate()."""
    rate_description = chargeback_rates
    db_client = appliance.db.client
    cb_rates = db_client['chargeback_rates']
    cb_rate_details = db_client['chargeback_rate_details']
    cb_tiers = db_client['chargeback_tiers']

    rate_tiers = []

    with db_client.transaction:
        result = (
            db_client.session.query(cb_rates, cb_rate_details, cb_tiers)
            .filter(cb_rates.id == cb_rate_details.chargeback_rate_id)
            .filter(cb_rate_details.id == cb_tiers.chargeback_rate_detail_id)
            .filter(cb_rates.description == rate_description)
            .all()
        )
        for row in result:
            rate_tier = {}
            for index, fields in enumerate(RATE_FIELDS):
                rate_tier.update(
                    {var: getattr(row[index], var) for var in fields})
            rate_tiers.append(rate_tier)
    logger.info(f"chargeback_rate_tiers = {rate_tiers}")
    return rate_tiers


@pytest.fixture(scope="module")
def chargeback_costs(appliance, chargeback_vm, chargeback_rate_tiers, resource_totals):
    """Check which tier the resource value belongs to, then calculate the cost based on the fixed
    and variable rates. Convert to per unit time for resource usage values, but not for resource
    allocation values."""
    costs = {}
    for resource in RESOURCES:
        costs[resource.cost_name] = {}
        for ts in resource_totals[resource.name]:
            costs[resource.cost_name][ts] = calculate_cost(resource,
                resource_totals[resource.name][ts],
                chargeback_rate_tiers)
    return costs


@pytest.fixture(scope="module")
def chargeback_costs_parsed(chargeback_costs):
    CURRENCY = "$"
    parsed_costs = {}
    for name, costs in chargeback_costs.items():
        parsed_costs[name] = {}
        for ts, cost in costs.items():
            parsed_costs[name][ts] = Unit.parse(f"{CURRENCY}{cost:,.2f}")
    logger.info(f"chargeback_costs_parsed = {parsed_costs}")
    return parsed_costs


@pytest.fixture(scope="module")
def chargeback_report(appliance, assign_chargeback_user, assign_rates):
    """Create chargeback report."""
    chargeback_rate_description = assign_rates
    title = fauxfactory.gen_alphanumeric(25, chargeback_rate_description, '_')
    CHARGEBACK_REPORT_FIELDS = [
        'CPU Used',
        'CPU Used Cost',
        'Disk I/O Used',
        'Disk I/O Used Cost',
        'Memory Used',
        'Memory Used Cost',
        'Network I/O Used',
        'Network I/O Used Cost',
        'Storage Used',
        'Storage Used Cost',
        'Memory Allocated over Time Period',
        'Memory Allocated Cost',
        'vCPUs Allocated over Time Period',
        'vCPUs Allocated Cost',
        'Storage Allocated',
        'Storage Allocated Cost',
        'Owner'
    ]
    data = {
        'menu_name': title,
        'title': title,
        'base_report_on': 'Chargeback for Vms',
        'report_fields': CHARGEBACK_REPORT_FIELDS,
        'filter': {
            'filter_show_costs': 'Owner',
            'filter_owner': assign_chargeback_user.name,
            'interval_end': 'Today (partial)',
            'interval_size': '2 Days'
        }
    }
    report = appliance.collections.reports.create(**data)
    logger.info(f"Created chargeback report {title!r}.")

    yield report

    if report.exists:
        report.delete()
    logger.info(f"Deleted chargeback report {title!r}.")


@pytest.fixture(scope="module")
def queue_chargeback_report(chargeback_report, hourly_rollups):
    chargeback_report.queue(wait_for_finish=True)
    regex = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    output = []
    for row in chargeback_report.saved_reports.all()[0].data.rows:
        if regex.match(row['Date Range']):
            output.append(row)
    if not output:
        pytest.skip("Empty chargeback report.")
    return output


@pytest.fixture(scope="module")
def chargeback_report_parsed(queue_chargeback_report):
    parsed_output = {}
    for resource in RESOURCES:
        parsed_output[resource.name] = {}
        parsed_output[resource.cost_name] = {}
        for row in queue_chargeback_report:
            ts = row['Date Range']
            parsed_output[resource.name][ts] = Unit.parse(row[resource.report_column])
            parsed_output[resource.cost_name][ts] = Unit.parse(row[resource.cost_report_column])
    logger.info(f"chargeback_report_parsed = {parsed_output}")
    return parsed_output


@pytest.fixture(scope="module")
def metering_report(appliance, assign_chargeback_user):
    """Create a metering report."""
    METERING_REPORT_FIELDS = [
        'Owner',
        'Memory Used',
        'CPU Used',
        'Disk I/O Used',
        'Network I/O Used',
        'Storage Used',
        'Existence Hours Metric',
        'Metering Used Metric',
    ]
    data = {
        'menu_name': assign_chargeback_user.name,
        'title': assign_chargeback_user.name,
        'base_report_on': 'Metering for VMs',
        'report_fields': METERING_REPORT_FIELDS,
        'filter': {
            'filter_show_costs': 'Owner',
            'filter_owner': assign_chargeback_user.name,
            'interval_end': 'Today (partial)',
            'interval_size': '2 Days'
        }
    }
    report = appliance.collections.reports.create(**data)

    yield report

    if report.exists:
        report.delete()


@pytest.fixture(scope="module")
def queue_metering_report(metering_report, hourly_rollups):
    logger.info(f"Queuing metering report {metering_report.title!r}.")
    metering_report.queue(wait_for_finish=True)

    report_output = list(metering_report.saved_reports.all()[0].data.rows)
    if not report_output:
        pytest.skip("Empty report")
    yield report_output
