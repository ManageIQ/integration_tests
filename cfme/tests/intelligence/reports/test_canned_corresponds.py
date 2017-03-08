# -*- coding: utf-8 -*-
import pytest
from functools import partial

from cfme.infrastructure.provider import InfraProvider, details_page
from cfme.intelligence.reports.reports import CannedSavedReport
from utils.appliance.implementations.ui import navigate_to
from utils.net import ip_address, resolve_hostname
from utils.providers import get_crud_by_name, setup_a_provider as _setup_a_provider, ProviderFilter
from utils.appliance import get_or_create_current_appliance
from utils import version
from cfme import test_requirements

provider_props = partial(details_page.infoblock.text, "Properties")


@pytest.fixture(scope="module")
def setup_a_provider():
    try:
        _setup_a_provider(filters=[ProviderFilter(classes=[InfraProvider])])
    except Exception:
        pytest.skip("It's not possible to set up any providers, therefore skipping")


@pytest.mark.tier(3)
@test_requirements.report
def test_providers_summary(soft_assert, setup_a_provider):
    """Checks some informations about the provider. Does not check memory/frequency as there is
    presence of units and rounding."""
    path = ["Configuration Management", "Providers", "Providers Summary"]
    report = CannedSavedReport.new(path)
    for provider in report.data.rows:
        if any(ptype in provider["MS Type"] for ptype in {"ec2", "openstack"}):  # Skip cloud
            continue
        navigate_to(InfraProvider(name=provider["Name"]), 'Details')
        hostname = version.pick({
            version.LOWEST: ("Hostname", "Hostname"),
            "5.5": ("Host Name", "Hostname")})
        soft_assert(
            provider_props(hostname[0]) == provider[hostname[1]],
            "Hostname does not match at {}".format(provider["Name"]))

        if version.current_version() < "5.4":
            # In 5.4, hostname and IP address are shared under Hostname (above)
            soft_assert(
                provider_props("IP Address") == provider["IP Address"],
                "IP Address does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("Aggregate Host CPU Cores") == provider["Total Number of Logical CPUs"],
            "Logical CPU count does not match at {}".format(provider["Name"]))

        soft_assert(
            provider_props("Aggregate Host CPUs") == provider["Total Number of Physical CPUs"],
            "Physical CPU count does not match at {}".format(provider["Name"]))


@pytest.mark.tier(3)
@test_requirements.report
def test_cluster_relationships(soft_assert, setup_a_provider):
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
def test_operations_vm_on(soft_assert, setup_a_provider):

    appliance = get_or_create_current_appliance()
    adb = appliance.db
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

    if len(vms_in_db) == len(list(report.data.rows)):
        for vm in vms_in_db:
            store_path = '{}/{}'.format(vm.storages_name.encode('utf8'),
                                        vm.vm_location.encode('utf8'))
            for item in report.data.rows:
                if vm.vm_name.encode('utf8') == item['VM Name']:
                    if (vm.hosts_name.encode('utf8') == item['Host'] and
                        vm.storages_name.encode('utf8') == item['Datastore'] and
                        store_path == item['Datastore Path'] and
                        (str(vm.vm_last_scan).encode('utf8') == item['Last Analysis Time'] or
                            (str(vm.vm_last_scan).encode('utf8') == 'None' and
                             item['Last Analysis Time'] == '')
                         )):
                            continue
                    else:
                        pytest.fail("Found not matching items. db:{} report:{}".format(vm, item))
    else:
        pytest.fail("Lenghts of report and BD do not match. db count:{} report count:{}".format(
            len(vms_in_db), len(list(report.data.rows))))


@pytest.mark.tier(3)
@test_requirements.report
def test_datastores_summary(soft_assert, setup_a_provider):

    appliance = get_or_create_current_appliance()
    adb = appliance.db
    storages = adb['storages']
    vms = adb['vms']
    host_storages = adb['host_storages']

    path = ["Configuration Management", "Storage", "Datastores Summary"]
    report = CannedSavedReport.new(path)

    storages_in_db = adb.session.query(storages.store_type, storages.free_space,
                                       storages.total_space, storages.name, storages.id).all()

    if len(storages_in_db) == len(list(report.data.rows)):
        for store in storages_in_db:

            number_of_vms = adb.session.query(vms.id).filter(vms.storage_id == store.id).count()
            number_of_hosts = adb.session.query(host_storages.host_id).filter(
                host_storages.storage_id == store.id).count()

            for item in report.data.rows:
                if store.name.encode('utf8') == item['Datastore Name']:
                    if (store.store_type.encode('utf8') == item['Type'] and
                     extract_gb(store.free_space) == float(item['Free Space'].split(' ')[0]) and
                      extract_gb(store.total_space) == float(item['Total Space'].split(' ')[0]) and
                       int(number_of_hosts) == int(item['Number of Hosts']) and
                       int(number_of_vms) == int(item['Number of VMs'])):
                        continue
                    else:
                        pytest.fail("Found not matching items. db:{} report:{}".format(store, item))


def extract_gb(column):
    return round((float(column) / 1073741824), 1)
