import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.net import ip_address
from cfme.utils.net import resolve_hostname
from cfme.utils.providers import get_crud_by_name

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider(classes=[InfraProvider], scope='function'),
    test_requirements.report,
]


def compare(db_item, report_item):
    """If one of the item is unfilled, check that the other item is as well.
    If not, check that they contain the same information."""
    if db_item is not None or report_item != '':
        return db_item == report_item
    else:
        return db_item is None and report_item == ''


@pytest.mark.rhv3
def test_providers_summary(appliance, soft_assert, request, setup_provider):
    """Checks some informations about the provider. Does not check memory/frequency as there is
    presence of units and rounding.

    Metadata:
        test_flag: inventory

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/6h
    """
    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Providers",
        menu_name="Providers Summary"
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete)
    # Skip cloud and network providers as they don't share some attributes with infra providers
    # Also skip the embedded ansible provider
    skipped_providers = {"ec2", "openstack", "redhat_network", "embedded_ansible_automation"}
    for provider in report.data.rows:
        if provider["MS Type"] in skipped_providers:
            continue
        provider_object = appliance.collections.infra_providers.instantiate(InfraProvider,
                                                                            name=provider["Name"])
        details_view = navigate_to(provider_object, 'Details')
        props = details_view.entities.summary("Properties")

        hostname = "Hostname" if appliance.version > "5.11" else "Host Name"
        soft_assert(props.get_text_of(hostname) == provider["Hostname"],
                    "Hostname does not match at {}".format(provider["Name"]))

        cpu_cores = props.get_text_of("Aggregate Host CPU Cores")
        soft_assert(cpu_cores == provider["Total Number of Logical CPUs"],
                    "Logical CPU count does not match at {}".format(provider["Name"]))

        host_cpu = props.get_text_of("Aggregate Host CPUs")
        soft_assert(host_cpu == provider["Total Number of Physical CPUs"],
                    "Physical CPU count does not match at {}".format(provider["Name"]))


@pytest.mark.rhv3
def test_cluster_relationships(appliance, request, soft_assert, setup_provider):
    """Tests vm power options from on

    Metadata:
        test_flag: inventory

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/6h
    """

    report = appliance.collections.reports.instantiate(
        type="Relationships",
        subtype="Virtual Machines, Folders, Clusters",
        menu_name="Cluster Relationships"
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete)

    for relation in report.data.rows:
        name = relation["Name"]
        provider_name = relation["Provider Name"]
        if not provider_name.strip():
            # If no provider name specified, ignore it
            continue
        provider = get_crud_by_name(provider_name)
        host_name = relation["Host Name"].strip()
        cluster_list = provider.mgmt.list_clusters() if isinstance(
            provider, SCVMMProvider) else provider.mgmt.list_cluster()
        verified_cluster = [item for item in cluster_list if name in item]
        soft_assert(verified_cluster, "Cluster {} not found in {}".format(name, provider_name))
        if not host_name:
            continue  # No host name
        host_ip = resolve_hostname(host_name, force=True)
        if host_ip is None:
            # Don't check
            continue

        host_list = provider.mgmt.list_host()
        for host in host_list:
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


@pytest.mark.rhv2
def test_operations_vm_on(
        soft_assert, temp_appliance_preconfig_funcscope, request, setup_provider_temp_appliance
):
    """Tests vm power options from on

    Metadata:
        test_flag: report

    Bugzilla:
        1571254

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/6h
    """
    appliance = temp_appliance_preconfig_funcscope
    adb = appliance.db.client
    vms = adb['vms']
    hosts = adb['hosts']
    storages = adb['storages']

    report = appliance.collections.reports.instantiate(
        type="Operations",
        subtype="Virtual Machines",
        menu_name="Online VMs (Powered On)"
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete)

    vms_in_db = adb.session.query(
        vms.name.label('vm_name'),
        vms.location.label('vm_location'),
        vms.last_scan_on.label('vm_last_scan'),
        storages.name.label('storages_name'),
        hosts.name.label('hosts_name')).outerjoin(
            hosts, vms.host_id == hosts.id).outerjoin(
                storages, vms.storage_id == storages.id).filter(
                    vms.power_state == 'on').order_by(vms.name).all()

    assert len(vms_in_db) == len(list(report.data.rows))
    vm_names = [vm.vm_name for vm in vms_in_db]
    for vm in vms_in_db:
        # Following check is based on BZ 1504010
        assert vm_names.count(vm.vm_name) == 1, (
            'There is a duplicate entry in DB for VM {}'.format(vm.vm_name))
        store_path = vm.vm_location
        if vm.storages_name:
            store_path = '{}/{}'.format(vm.storages_name, store_path)
        for item in report.data.rows:
            if vm.vm_name == item['VM Name']:
                assert compare(vm.hosts_name, item['Host'])
                assert compare(vm.storages_name, item['Datastore'])
                assert compare(store_path, item['Datastore Path'])
                assert compare(vm.vm_last_scan, item['Last Analysis Time'])


@pytest.mark.rhv3
def test_datastores_summary(
        soft_assert, temp_appliance_preconfig_funcscope, request, setup_provider_temp_appliance
):
    """Checks Datastores Summary report with DB data. Checks all data in report, even rounded
    storage sizes.

    Metadata:
        test_flag: inventory

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: high
        initialEstimate: 1/6h
    """
    appliance = temp_appliance_preconfig_funcscope
    adb = appliance.db.client
    storages = adb['storages']
    vms = adb['vms']
    host_storages = adb['host_storages']

    report = appliance.collections.reports.instantiate(
        type="Configuration Management",
        subtype="Storage",
        menu_name="Datastores Summary"
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete)

    storages_in_db = adb.session.query(storages.store_type, storages.free_space,
                                       storages.total_space, storages.name, storages.id).all()

    assert len(storages_in_db) == len(list(report.data.rows))

    storages_in_db_list = []
    report_rows_list = []

    for store in storages_in_db:

        number_of_vms = adb.session.query(vms.id).filter(
            vms.storage_id == store.id).filter(
                vms.template == 'f').count()

        number_of_hosts = adb.session.query(host_storages.host_id).filter(
            host_storages.storage_id == store.id).count()

        store_dict = {
            'Datastore Name': store.name,
            'Type': store.store_type,
            'Free Space': round_num(store.free_space),
            'Total Space': round_num(store.total_space),
            'Number of Hosts': int(number_of_hosts),
            'Number of VMs': int(number_of_vms)
        }

        storages_in_db_list.append(store_dict)

    for row in report.data.rows:

        row['Free Space'] = extract_num(row['Free Space'])
        row['Total Space'] = extract_num(row['Total Space'])
        row['Number of Hosts'] = int(row['Number of Hosts'])
        row['Number of VMs'] = int(row['Number of VMs'])

        report_rows_list.append(row)
    assert sorted(storages_in_db_list, key=str) == sorted(report_rows_list, key=str)


def round_num(column):
    num = float(column)

    while num > 1024:
        num /= 1024.0

    return round(num, 1)


def extract_num(column):
    return float(column.split(' ')[0])
