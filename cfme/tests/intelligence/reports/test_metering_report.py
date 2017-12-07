# -*- coding: utf-8 -*-

import cfme.configure.access_control as ac
import fauxfactory
import math
import pytest
import re

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.common.vm import VM
from cfme.common.provider import BaseProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.intelligence.reports.reports import CustomReport
from datetime import date
from fixtures.provider import setup_or_skip
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.uncollectif(lambda: current_version() < "5.9"),
    pytest.mark.meta(blockers=[BZ(1433984, forced_streams=["5.7", "5.8", "upstream"]),
                               BZ(1468729, forced_streams=["5.9"]),
                               BZ(1511099, forced_streams=["5.7", "5.8"],
                                  unblock=lambda provider: not provider.one_of(GCEProvider))]),
    pytest.mark.provider([VMwareProvider, RHEVMProvider, AzureProvider, GCEProvider],
                         scope='module',
                         required_fields=[(['cap_and_util', 'test_chargeback'], True)]),
    test_requirements.chargeback,
]


@pytest.yield_fixture(scope="module")
def clean_setup_provider(request, provider):
    BaseProvider.clear_providers()
    setup_or_skip(request, provider)
    yield
    BaseProvider.clear_providers()


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='secret')


@pytest.yield_fixture(scope="module")
def vm_ownership(enable_candu, clean_setup_provider, provider, appliance):
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
    user = ac.User(name=provider.name + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='abc@example.com',
        group=cb_group,
        cost_center='Workload',
        value_assign='Database')

    vm = VM.factory(vm_name, provider)

    try:
        user.create()
        vm.set_ownership(user=user.name)
        logger.info('Assigned VM OWNERSHIP for {} running on {}'.format(vm_name, provider.name))

        yield user.name
    finally:
        vm.unset_ownership()
        user.delete()


@pytest.yield_fixture(scope="module")
def enable_candu(provider, appliance):
    # C&U data collection consumes a lot of memory and CPU.So, we are disabling some server roles
    # that are not needed for Chargeback reporting.

    server_info = appliance.server.settings
    original_roles = server_info.server_roles_db
    server_info.enable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    server_info.disable_server_roles('automate', 'smartstate')
    command = ('Metric::Targets.perf_capture_always = {:storage=>true, :host_and_cluster=>true};')
    appliance.ssh_client.run_rails_command(command, timeout=None)

    yield

    server_info.update_server_roles_db(original_roles)
    command = ('Metric::Targets.perf_capture_always = {:storage=>false, :host_and_cluster=>false};')
    appliance.ssh_client.run_rails_command(command, timeout=None)


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
            vm.perf_capture('realtime', 4.hour.ago.utc, Time.now.utc)\""
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
        vm.perf_rollup_range(4.hour.ago.utc, Time.now.utc,'realtime')\"".
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

    return {"cpu_used": average_cpu_used_in_mhz,
            "memory_used": average_memory_used_in_mb,
            "network_io": average_network_io,
            "disk_io_used": average_disk_io,
            "storage_used": average_storage_used,
            "consumed_hours": consumed_hours}


@pytest.yield_fixture(scope="module")
def metering_report(vm_ownership, provider):
    # Create a Metering report based; Queue the report.
    owner = vm_ownership
    data = {
        'menu_name': 'cb_' + provider.name,
        'title': 'cb_' + provider.name,
        'base_report_on': 'Metering for VMs',
        'report_fields': ['Owner', 'Memory Used',
        'CPU Used', 'Disk I/O Used',
        'Network I/O Used', 'Storage Used',
        'Existence Hours Metric', 'Metering Used Metric'],
        'filter': {
            'filter_show_costs': 'Owner',
            'filter_owner': owner,
            'interval_end': 'Today (partial)'
        }
    }
    report = CustomReport(is_candu=True, **data)
    report.create()

    logger.info('Queuing chargeback report with default rate for {} provider'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.get_saved_reports()[0].data.rows)
    report.delete()


# Tests to validate costs reported in the Chargeback report for various metrics.
# The costs reported in the Chargeback report should be approximately equal to the
# costs estimated in the chargeback_costs_default/chargeback_costs_custom fixtures.
@pytest.mark.uncollectif(
    lambda provider: provider.category == 'cloud')
def test_validate_cpu_usage(resource_usage, metering_report):
    """Test to validate CPU usage.
       Calculation is based on default Chargeback rate.
    """
    for groups in metering_report:
        if groups["CPU Used"]:
            estimated_cpu_usage = resource_usage['cpu_used']
            usage_from_report = groups["CPU Used"]
            usage = re.sub(r'[MHz,]', r'', usage_from_report)
            assert estimated_cpu_usage - 1.0 <= float(usage) \
                <= estimated_cpu_usage + 1.0, 'Estimated cost and report cost do not match'
            break


@pytest.mark.uncollectif(
    lambda provider: provider.one_of(GCEProvider))
def test_validate_memory_usage(resource_usage,
        metering_report):
    """Test to validate memory usage.
       Calculation is based on default Chargeback rate.

    """
    for groups in metering_report:
        if groups["Memory Used"]:
            estimated_memory_usage = resource_usage['memory_used']
            usage_from_report = groups["Memory Used"]
            usage = re.sub(r'[$,]', r'', usage_from_report)
            assert estimated_memory_usage - 1.0 <= float(usage) \
                <= estimated_memory_usage + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_network_usage(resource_usage,
        metering_report):
    """Test to validate network usage cost.
       Calculation is based on default Chargeback rate.

    """
    for groups in metering_report:
        if groups["Network I/O Used"]:
            estimated_network_usage = resource_usage['network_io']
            usage_from_report = groups["Network I/O Used"]
            usage = re.sub(r'[KBps,]', r'', usage_from_report)
            assert estimated_network_usage - 1.0 <= float(usage) \
                <= estimated_network_usage + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_disk_usage(resource_usage, metering_report):
    """Test to validate disk usage cost.
       Calculation is based on default Chargeback rate.

    """
    for groups in metering_report:
        if groups["Disk I/O Used"]:
            estimated_disk_usage = resource_usage['disk_io_used']
            usage_from_report = groups["Disk I/O Used"]
            usage = re.sub(r'[KBps,]', r'', usage_from_report)
            assert estimated_disk_usage - 1.0 <= float(usage) \
                <= estimated_disk_usage + 1.0, 'Estimated cost and report cost do not match'
            break


def test_validate_storage_usage(resource_usage,
        metering_report):
    """Test to validate stoarge usage cost.
       Calculation is based on default Chargeback rate.
    """
    for groups in metering_report:
        if groups["Storage Used"]:
            estimated_storage_usage = resource_usage['storage_used']
            usage_from_report = groups["Storage Used"]
            usage = re.sub(r'[$,]', r'', usage_from_report)
            assert estimated_storage_usage - 1.0 <= float(usage) \
                <= estimated_storage_usage + 1.0, 'Estimated cost and report cost do not match'
            break
