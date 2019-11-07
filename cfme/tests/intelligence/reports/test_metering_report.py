# All providers that support C&U support Metering Reports.SCVMM doesn't support C&U.
# Metering reports differ from Chargeback reports in that Metering reports report
# only resource usage and not costs.
#
# Metering Reports have been introduced in 59.
import math
import re
from datetime import date

import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.provider import BaseProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
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
    test_requirements.chargeback,
]

# Allowed deviation between the reported value in the Metering report and the estimated value.
DEVIATION = 1


@pytest.fixture(scope="module")
def clean_setup_provider(request, has_no_providers_modscope, setup_provider_modscope,
        provider):
    yield
    BaseProvider.clear_providers()


@pytest.fixture(scope="module")
def vm_ownership(enable_candu, clean_setup_provider, provider, appliance):
    # In these tests, Metering report is filtered on VM owner.So,VMs have to be
    # assigned ownership.

    vm_name = provider.data['cap_and_util']['chargeback_vm']

    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(vm_name, provider)

    if not vm.exists_on_provider:
        pytest.skip("Skipping test, {} VM does not exist".format(vm_name))
    vm.mgmt.ensure_state(VmState.RUNNING)

    group_collection = appliance.collections.groups
    cb_group = group_collection.instantiate(description='EvmGroup-user')
    user = appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric(),
        credential=Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
            secret='secret'),
        email='abc@example.com',
        groups=cb_group,
        cost_center='Workload',
        value_assign='Database')

    try:
        vm.set_ownership(user=user)
        logger.info('Assigned VM OWNERSHIP for {} running on {}'.format(vm_name, provider.name))

        yield user.name
    finally:
        vm.unset_ownership()
        user.delete()


@pytest.fixture(scope="module")
def enable_candu(provider, appliance):
    # C&U data collection consumes a lot of memory and CPU.So, we are disabling some server roles
    # that are not needed for Metering reports.

    server_info = appliance.server.settings
    original_roles = server_info.server_roles_db
    server_info.enable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    server_info.disable_server_roles('automate', 'smartstate')
    # We are enabling C&U data capture for 1)all hosts and clusters and 2)all datastores.
    # On the UI, this can be set through the Configuration -> Settings -> Region -> C&U collection
    # tab.
    command = ('Metric::Targets.perf_capture_always = {:storage=>true, :host_and_cluster=>true};')
    appliance.ssh_client.run_rails_command(command, timeout=None)

    yield

    server_info.update_server_roles_db(original_roles)
    command = ('Metric::Targets.perf_capture_always = {:storage=>false, :host_and_cluster=>false};')
    appliance.ssh_client.run_rails_command(command, timeout=None)


def verify_records_rollups_table(appliance, provider, vm_name):
    # Verify that hourly rollups are present in the metric_rollups table.
    ems = appliance.db.client['ext_management_systems']
    rollups = appliance.db.client['metric_rollups']

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(rollups.capture_interval_name == 'hourly',
                    rollups.resource_name == vm_name,
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
    cpu_used_in_mhz = 0
    memory_used_in_mb = 0
    network_io = 0
    disk_io = 0
    storage_used = 0

    vm_name = provider.data['cap_and_util']['chargeback_vm']
    metrics = appliance.db.client['metrics']
    rollups = appliance.db.client['metric_rollups']
    ems = appliance.db.client['ext_management_systems']
    logger.info('Deleting METRICS DATA from metrics and metric_rollups tables')

    appliance.db.client.session.query(metrics).delete()
    appliance.db.client.session.query(rollups).delete()

    # Metering reports are done on hourly and daily rollup values and not real-time values.So, we
    # are capturing C&U data and forcing hourly rollups by running these commands through
    # the Rails console.
    #
    # Metering reports differ from Chargeback reports in that Metering reports 1)report only
    # resource usage and not costs and 2)sum total of resource usage is reported instead of
    # the average usage.For eg:If we have 24 hourly rollups, resource usage in a Metering report
    # is the sum of these 24 rollups, whereas resource usage in a Chargeback report is the
    # average of these 24 rollups. So, we need data from at least 2 hours in order to validate that
    # the resource usage is actually being summed up.

    def verify_records_metrics_table(appliance, provider, vm_name):
        # Verify that rollups are present in the metric_rollups table.

        ems = appliance.db.client['ext_management_systems']
        metrics = appliance.db.client['metrics']

        # Capture real-time C&U data
        ret = appliance.ssh_client.run_rails_command(
            "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
            vm.perf_capture('realtime', 2.hour.ago.utc, Time.now.utc)\""
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
            if (record.cpu_usagemhz_rate_average or
               record.cpu_usage_rate_average or
               record.derived_memory_used or
               record.net_usage_rate_average or
               record.disk_usage_rate_average):
                return True
        return False

    wait_for(verify_records_metrics_table, [appliance, provider, vm_name], timeout=600,
        fail_condition=False, message='Waiting for VM real-time data')

    # New C&U data may sneak in since 1)C&U server roles are running and 2)collection for clusters
    # and hosts is on.This would mess up our calculations, so we are disabling C&U
    # collection after data has been fetched for the last two hours.

    appliance.server.settings.disable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector')
    # Perfrom rollup of C&U data.
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_rollup_range(2.hour.ago.utc, Time.now.utc,'realtime')\"".
        format(provider.id, repr(vm_name)))
    assert ret.success, "Failed to rollup VM C&U data:".format(ret.out)

    wait_for(verify_records_rollups_table, [appliance, provider, vm_name], timeout=600,
        fail_condition=False, message='Waiting for hourly rollups')

    # Since we are collecting C&U data for > 1 hour, there will be multiple hourly records per VM
    # in the metric_rollups DB table.The values from these hourly records are summed up.

    with appliance.db.client.transaction:
        result = (
            appliance.db.client.session.query(rollups.id)
            .join(ems, rollups.parent_ems_id == ems.id)
            .filter(rollups.capture_interval_name == 'hourly',
                    rollups.resource_name == vm_name,
                    ems.name == provider.name, rollups.timestamp >= date.today())
        )

    for record in appliance.db.client.session.query(rollups).filter(
            rollups.id.in_(result.subquery())):
        cpu_used_in_mhz = cpu_used_in_mhz + record.cpu_usagemhz_rate_average
        memory_used_in_mb = memory_used_in_mb + record.derived_memory_used
        network_io = network_io + record.net_usage_rate_average
        disk_io = disk_io + record.disk_usage_rate_average
        storage_used = storage_used + record.derived_vm_used_disk_storage

    # Convert storage used in Bytes to GB
    storage_used = storage_used * math.pow(2, -30)

    return {"cpu_used": cpu_used_in_mhz,
            "memory_used": memory_used_in_mb,
            "network_io": network_io,
            "disk_io_used": disk_io,
            "storage_used": storage_used}


@pytest.fixture(scope="module")
def metering_report(appliance, vm_ownership, provider):
    # Create a Metering report based on VM owner; Queue the report.
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
    report = appliance.collections.reports.create(is_candu=True, **data)

    logger.info('Queuing Metering report for {} provider'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.saved_reports.all()[0].data.rows)
    report.delete()


# Tests to validate usage reported in the Metering report for various metrics.
# The usage reported in the report should be approximately equal to the
# usage estimated in the resource_usage fixture, therefore a small deviation is fine.
@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_cloud],
                      override=True,
                      scope='module')
def test_validate_cpu_usage(resource_usage, metering_report):
    """Test to validate CPU usage.This metric is not collected for cloud providers.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        casecomponent: Reporting
        initialEstimate: 1/4h
    """
    for groups in metering_report:
        if groups["CPU Used"]:
            estimated_cpu_usage = resource_usage['cpu_used']
            usage_from_report = groups["CPU Used"]
            if 'GHz' in usage_from_report:
                estimated_cpu_usage = estimated_cpu_usage * math.pow(2, -10)
            usage = re.sub(r'(MHz|GHz|,)', r'', usage_from_report)
            assert estimated_cpu_usage - DEVIATION <= float(usage) \
                <= estimated_cpu_usage + DEVIATION, 'Estimated cost and report cost do not match'
            break


@pytest.mark.provider(gen_func=providers,
                      filters=[cloud_and_infra, not_scvmm, not_ec2_gce],
                      override=True,
                      scope='module')
def test_validate_memory_usage(resource_usage, metering_report):
    """Test to validate memory usage.This metric is not collected for GCE, EC2.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Reporting
    """
    for groups in metering_report:
        if groups["Memory Used"]:
            estimated_memory_usage = resource_usage['memory_used']
            usage_from_report = groups["Memory Used"]
            if 'GB' in usage_from_report:
                estimated_memory_usage = estimated_memory_usage * math.pow(2, -10)
            usage = re.sub(r'(MB|GB|,)', r'', usage_from_report)
            assert estimated_memory_usage - DEVIATION <= float(usage) \
                <= estimated_memory_usage + DEVIATION, 'Estimated cost and report cost do not match'
            break


def test_validate_network_usage(resource_usage, metering_report):
    """Test to validate network usage.

    Polarion:
        assignee: tpapaioa
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Reporting
    """
    for groups in metering_report:
        if groups["Network I/O Used"]:
            estimated_network_usage = resource_usage['network_io']
            usage_from_report = groups["Network I/O Used"]
            usage = re.sub(r'(KBps|,)', r'', usage_from_report)
            assert estimated_network_usage - DEVIATION <= float(usage) \
                <= estimated_network_usage + DEVIATION,\
                'Estimated cost and report cost do not match'
            break


def test_validate_disk_usage(resource_usage, metering_report):
    """Test to validate disk usage.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Reporting
    """
    for groups in metering_report:
        if groups["Disk I/O Used"]:
            estimated_disk_usage = resource_usage['disk_io_used']
            usage_from_report = groups["Disk I/O Used"]
            usage = re.sub(r'(KBps|,)', r'', usage_from_report)
            assert estimated_disk_usage - DEVIATION <= float(usage) \
                <= estimated_disk_usage + DEVIATION, 'Estimated cost and report cost do not match'
            break


def test_validate_storage_usage(resource_usage, metering_report):
    """Test to validate storage usage.

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Reporting
    """
    for groups in metering_report:
        if groups["Storage Used"]:
            estimated_storage_usage = resource_usage['storage_used']
            usage_from_report = groups["Storage Used"]
            usage = re.sub(r'(MB|GB|,)', r'', usage_from_report)
            assert estimated_storage_usage - DEVIATION <= float(usage) \
                <= estimated_storage_usage + DEVIATION, \
                'Estimated cost and report cost do not match'
            break
