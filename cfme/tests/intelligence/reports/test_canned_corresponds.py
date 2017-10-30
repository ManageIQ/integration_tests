# -*- coding: utf-8 -*-
import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.intelligence.reports.reports import CannedSavedReport
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.net import ip_address, resolve_hostname
from cfme.utils.providers import get_crud_by_name
from cfme.utils import testgen
from cfme import test_requirements


pytest_generate_tests = testgen.generate(classes=[InfraProvider], scope='module')


@pytest.mark.tier(3)
@pytest.mark.usefixtures('setup_provider')
@test_requirements.report
def test_providers_summary(soft_assert):
    """Checks some informations about the provider. Does not check memory/frequency as there is
    presence of units and rounding."""
    path = ["Configuration Management", "Providers", "Providers Summary"]
    report = CannedSavedReport.new(path)
    for provider in report.data.rows:
        if any(ptype in provider["MS Type"] for ptype in {"ec2", "openstack"}):  # Skip cloud
            continue
        details_view = navigate_to(InfraProvider(name=provider["Name"]), 'Details')
        props = details_view.entities.properties

        hostname = ("Host Name", "Hostname")
        soft_assert(props.get_text_of(hostname[0]) == provider[hostname[1]],
                    "Hostname does not match at {}".format(provider["Name"]))

        cpu_cores = props.get_text_of("Aggregate Host CPU Cores")
        soft_assert(cpu_cores == provider["Total Number of Logical CPUs"],
                    "Logical CPU count does not match at {}".format(provider["Name"]))

        host_cpu = props.get_text_of("Aggregate Host CPUs")
        soft_assert(host_cpu == provider["Total Number of Physical CPUs"],
                    "Physical CPU count does not match at {}".format(provider["Name"]))


@pytest.mark.tier(3)
@pytest.mark.usefixtures('setup_provider')
@test_requirements.report
def test_cluster_relationships(soft_assert):
    path = ["Relationships", "Virtual Machines, Folders, Clusters", "Cluster Relationships"]
    report = CannedSavedReport.new(path)
    for relation in report.data.rows:
        name = relation["Name"]
        provider_name = relation["Provider Name"]
        if not provider_name.strip():
            # If no provider name specified, ignore it
            continue
        provider = get_crud_by_name(provider_name).mgmt
        host_name = relation["Host Name"].strip()
        soft_assert(name in provider.list_cluster(), "Cluster {} not found in {}".format(
            name, provider_name
        ))
        if not host_name:
            continue  # No host name
        host_ip = resolve_hostname(host_name, force=True)
        if host_ip is None:
            # Don't check
            continue
        for host in provider.list_host():
            if ip_address.match(host) is None:
                host_is_ip = False
                ip_from_provider = resolve_hostname(host, force=True)
            else:
                host_is_ip = True
                ip_from_provider = host
            if not host_is_ip:
                # Strings first
                if host == host_name:
                    break
                elif host_name.startswith(host):
                    break
                elif ip_from_provider is not None and ip_from_provider == host_ip:
                    break
            else:
                if host_ip == ip_from_provider:
                    break
        else:
            soft_assert(False, "Hostname {} not found in {}".format(host_name, provider_name))


@pytest.mark.tier(3)
@test_requirements.report
@pytest.mark.usefixtures('setup_provider')
@pytest.mark.meta(blockers=[BZ(1504010, forced_streams=['5.7', '5.8', 'upstream'])])
def test_operations_vm_on(soft_assert, appliance):

    adb = appliance.db.client
    vms = adb['vms']
    hosts = adb['hosts']
    storages = adb['storages']

    path = ["Operations", "Virtual Machines", "Online VMs (Powered On)"]
    report = CannedSavedReport.new(path)

    vms_in_db = adb.session.query(
        vms.name.label('vm_name'),
        vms.location.label('vm_location'),
        vms.last_scan_on.label('vm_last_scan'),
        storages.name.label('storages_name'),
        hosts.name.label('hosts_name')).join(
            hosts, vms.host_id == hosts.id).join(
                storages, vms.storage_id == storages.id).filter(
                    vms.power_state == 'on').order_by(vms.name).all()

    assert len(vms_in_db) == len(list(report.data.rows))
    vm_names = [vm.vm_name for vm in vms_in_db]
    for vm in vms_in_db:
        # Following check is based on BZ 1504010
        assert vm_names.count(vm.vm_name) == 1, \
            'There is a duplicate entry in DB for VM {}'.format(vm.vm_name)
        store_path = '{}/{}'.format(vm.storages_name.encode('utf8'),
                                    vm.vm_location.encode('utf8'))
        for item in report.data.rows:
            if vm.vm_name.encode('utf8') == item['VM Name']:
                assert vm.hosts_name.encode('utf8') == item['Host']
                assert vm.storages_name.encode('utf8') == item['Datastore']
                assert store_path == item['Datastore Path']
                assert (str(vm.vm_last_scan).encode('utf8') == item['Last Analysis Time'] or
                 (str(vm.vm_last_scan).encode('utf8') == 'None' and
                 item['Last Analysis Time'] == ''))


@pytest.mark.tier(3)
@test_requirements.report
@pytest.mark.usefixtures('setup_provider')
def test_datastores_summary(soft_assert, appliance):
    """Checks Datastores Summary report with DB data. Checks all data in report, even rounded
    storage sizes."""

    adb = appliance.db.client
    storages = adb['storages']
    vms = adb['vms']
    host_storages = adb['host_storages']

    path = ["Configuration Management", "Storage", "Datastores Summary"]
    report = CannedSavedReport.new(path)

    storages_in_db = adb.session.query(storages.store_type, storages.free_space,
                                       storages.total_space, storages.name, storages.id).all()

    assert len(storages_in_db) == len(list(report.data.rows))
    for store in storages_in_db:

        number_of_vms = adb.session.query(vms.id).filter(
            vms.storage_id == store.id).filter(
                vms.template == 'f').count()
        number_of_hosts = adb.session.query(host_storages.host_id).filter(
            host_storages.storage_id == store.id).count()

        for item in report.data.rows:
            if store.name.encode('utf8') == item['Datastore Name']:
                assert store.store_type.encode('utf8') == item['Type']
                assert round_num(store.free_space) == extract_num(item['Free Space'])
                assert round_num(store.total_space) == extract_num(item['Total Space'])
                assert int(number_of_hosts) == int(item['Number of Hosts'])
                assert int(number_of_vms) == int(item['Number of VMs'])


def round_num(column):
    num = float(column)

    while num > 1024:
        num /= 1024.0

    return round(num, 1)


def extract_num(column):
    return float(column.split(' ')[0])
