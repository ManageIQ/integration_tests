from collections import namedtuple

import fauxfactory
import pytest
from cinderclient.exceptions import BadRequest
from manageiq_client.filters import Q
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import setup_or_skip
from cfme.fixtures.templates import _get_template
from cfme.fixtures.templates import Templates
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import conf
from cfme.utils import ssh
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from cfme.v2v.infrastructure_mapping import InfrastructureMapping as InfraMapping


FormDataVmObj = namedtuple("FormDataVmObj", ["infra_mapping_data", "vm_list"])
V2vProviders = namedtuple("V2vProviders", ["vmware_provider", "rhv_provider", "osp_provider"])


def set_skip_event_history_flag(appliance):
    """This flag is required for OSP to skip all old events and refresh inventory"""
    config = appliance.advanced_settings
    if not config['ems']['ems_openstack']['event_handling']['event_skip_history']:
        appliance.update_advanced_settings(
            {'ems': {'ems_openstack': {'event_handling': {'event_skip_history': True}}}})
        appliance.evmserverd.restart()
        appliance.evmserverd.wait_for_running()
        appliance.wait_for_miq_ready()


def _start_event_workers_for_osp(appliance, provider):
    """This is a workaround to start event catchers until BZ 1753364 is fixed"""
    provider_edit_view = navigate_to(provider, 'Edit', wait_for_view=30)
    endpoint_view = provider.endpoints_form(parent=provider_edit_view)
    endpoint_view.events.event_stream.select("AMQP")
    endpoint_view.events.event_stream.select("Ceilometer")
    provider_edit_view.save.click()

    def is_osp_worker_running():
        return "started" in appliance.ssh_client.run_rake_command(
            "evm:status | grep 'Openstack::Cloud::EventCatcher'"
        ).output

    # Wait for Eventcatcher workers to get started with in 60 sec
    try:
        wait_for(lambda: is_osp_worker_running, num_sec=60, delay=10)
    except TimedOutError:
        pytest.skip("Openstack Eventcatcher workers are not running")


@pytest.fixture(scope="module")
def v2v_provider_setup(request, appliance, source_provider, provider):
    """ Fixture to setup providers """
    vmware_provider, rhv_provider, osp_provider = None, None, None
    for v2v_provider in [source_provider, provider]:
        if v2v_provider.one_of(VMwareProvider):
            vmware_provider = v2v_provider
            setup_or_skip(request, vmware_provider)
        elif v2v_provider.one_of(RHEVMProvider):
            rhv_provider = v2v_provider
            setup_or_skip(request, rhv_provider)
        elif v2v_provider.one_of(OpenStackProvider):
            set_skip_event_history_flag(appliance)
            osp_provider = v2v_provider
            setup_or_skip(request, osp_provider)
            if BZ(1753364, forced_streams=['5.11']).blocks:
                _start_event_workers_for_osp(appliance, osp_provider)
        else:
            pytest.skip(f"Provider {provider.name} is not a valid provider for v2v tests")
    v2v_providers = V2vProviders(vmware_provider=vmware_provider,
                                 rhv_provider=rhv_provider,
                                 osp_provider=osp_provider)

    # Transformation method can be vddk or ssh
    transformation_method = request.param if hasattr(request, "param") else 'VDDK67'

    # set host credentials for Vmware and RHEV hosts
    __host_credentials(appliance, transformation_method, v2v_providers)

    yield v2v_providers
    for v2v_provider in v2v_providers:
        if v2v_provider is not None:
            v2v_provider.delete_if_exists(cancel=False)


def __host_credentials(appliance, transformation_method, v2v_providers): # noqa
    """ Sets up host credentials for vmware and rhv providers
        for RHEV migration.
        For migration with OSP only vmware(source) provider
        host credentials need to be added.
        These credentials are automatically removed once the
        provider is deleted in clean up.

    Args:
        appliance
        transformation_method : vddk or ssh to be used in configuring conversion host
        v2v_providers: vmware (and rhev in case of RHV migration ) , osp not needed.
    """
    provider_list = [v2v_providers.vmware_provider]

    if v2v_providers.rhv_provider is not None:
        provider_list.append(v2v_providers.rhv_provider)

    try:
        for v2v_provider in provider_list:
            hosts = v2v_provider.hosts.all()
            for host in hosts:
                try:
                    host_data, = [
                        data for data in v2v_provider.data["hosts"] if data["name"] == host.name]
                except ValueError:
                    pytest.skip("No host data")

                # TODO(BZ-1718209): Remove UI host authentication
                if not BZ(1718209).blocks:
                    host.update_credentials_rest(credentials=host_data['credentials'])
                else:
                    host_obj = appliance.collections.hosts.instantiate(
                        name=host.name,
                        provider=v2v_provider
                    )
                    with update(host_obj, validate_credentials=True):
                        host_obj.credentials = {
                            "default": Host.Credential.from_config(
                                host_data["credentials"]["default"]
                            )
                        }
    except Exception:
        logger.exception("Exception when trying to add the host credentials.")
        pytest.skip("No data for hosts in providers, failed to retrieve hosts and add creds.")

    # Configure conversion host for RHEV migration
    target_provider = (
        v2v_providers.osp_provider if v2v_providers.osp_provider else v2v_providers.rhv_provider)
    set_conversion_host_api(appliance,
                            transformation_method,
                            v2v_providers.vmware_provider,
                            target_provider)


def _tag_cleanup(host_obj, tag1, tag2):
    """
        Clean Up Tags

        Returns: Boolean True if all Tags were removed/cleaned
        or False means all required Tags are present on host.
    """

    def extract_tag(tag):
        # Following strip will remove extra asterisk from tag assignment
        return tag.category.display_name.strip(" *"), tag.display_name

    valid_tags = {extract_tag(tag1), extract_tag(tag2)}
    tags = host_obj.get_tags()
    tags_set = set(map(extract_tag, tags))
    # we always neeed 2 tags for migration, if total is less than 2
    # don't bother checking what tag was it, just remove it and
    # then add all required tags via add_tags() call. or if tags on host
    # are not subset of valid tags, we still remove them.
    if len(tags_set) < 2 or not tags_set.issubset(valid_tags):
        host_obj.remove_tags(tags=tags)
        return True
    return False


def create_tags(appliance, transformation_method):
    """
    Create tags V2V - Transformation Host * and V2V - Transformation Method
    Args:
        appliance:
        transformation_method: VDDK/SSH

    """
    # t is for True in V2V - Transformation Host * tag
    tag1 = appliance.collections.categories.instantiate(
        display_name="V2V - Transformation Host *"
    ).collections.tags.instantiate(display_name="t")
    tag2 = appliance.collections.categories.instantiate(
        display_name="V2V - Transformation Method"
    ).collections.tags.instantiate(display_name=transformation_method)
    return tag1, tag2


def vddk_url(transformation_method):
    """Get vddk url from cfme_data"""
    try:
        vddk_urls = conf.cfme_data.basic_info.vddk_url
    except (KeyError, AttributeError):
        pytest.skip("VDDK URLs not found in cfme_data.basic_info")
    url = vddk_urls.get(transformation_method)

    if url is None:
        pytest.skip(f"VDDK {transformation_method} is unavailable, skipping test")
    return url


def get_conversion_data(target_provider):
    if target_provider.one_of(RHEVMProvider):
        resource_type = "ManageIQ::Providers::Redhat::InfraManager::Host"
        engine_key = conf.credentials[target_provider.data["ssh_creds"]]
        auth_user = engine_key.username
        ssh_client = ssh.SSHClient(
            hostname=target_provider.hostname,
            username=engine_key.username,
            password=engine_key.password,
        )

        private_key = ssh_client.run_command(
            "cat /etc/pki/ovirt-engine/keys/engine_id_rsa").output
        try:
            hosts = [h.name for h in target_provider.hosts.all()]
        except KeyError:
            pytest.skip("No conversion host on provider")

    else:
        resource_type = "ManageIQ::Providers::Openstack::CloudManager::Vm"
        instance_key = conf.credentials[
            target_provider.data["private-keys"]["conversion_host_ssh_key"]["credentials"]]
        auth_user = instance_key.username
        private_key = instance_key.password
        try:
            hosts = target_provider.data["conversion_instances"]
        except KeyError:
            pytest.skip("No conversion instance on provider")

    return {
        "resource_type": resource_type,
        "private_key": private_key,
        "auth_user": auth_user,
        "hosts": hosts,
    }


def set_conversion_host_api(
        appliance, transformation_method, source_provider, target_provider):
    """Setting conversion host for RHV and OSP providers via REST"""
    vmware_ssh_private_key = None
    vmware_vddk_package_url = None

    delete_hosts = appliance.ssh_client.run_rails_command(
        "'MiqTask.delete_all; ConversionHost.delete_all'")
    if not delete_hosts.success:
        pytest.skip(
            f"Failed to delete all conversion hosts: {delete_hosts.output}")

    conversion_data = get_conversion_data(target_provider)
    if transformation_method == "SSH":
        vmware_key = conf.credentials[
            source_provider.data["private-keys"]["vmware-ssh-key"]["credentials"]]
        vmware_ssh_private_key = vmware_key.password
    else:
        vmware_vddk_package_url = vddk_url(transformation_method)

    for host in conversion_data["hosts"]:
        conversion_entity = "hosts" if target_provider.one_of(RHEVMProvider) else "vms"

        host_id = (
            getattr(appliance.rest_api.collections, conversion_entity).filter(
                Q.from_dict({"name": host})).resources[0].id)
        response = appliance.rest_api.collections.conversion_hosts.action.create(
            resource_id=host_id,
            resource_type=conversion_data["resource_type"],
            vmware_vddk_package_url=vmware_vddk_package_url,
            vmware_ssh_private_key=vmware_ssh_private_key,
            conversion_host_ssh_private_key=conversion_data["private_key"],
            auth_user=conversion_data["auth_user"])[0]
        response.reload()
        wait_for(
            lambda: response.task.state == "Finished",
            fail_func=response.task.reload,
            num_sec=600,
            delay=3,
            message="Waiting for conversion configuration task to be finished")


@pytest.fixture(scope="function")
def delete_conversion_hosts(appliance):
    # Delete existing conversion host entries from CFME
    delete_hosts = appliance.ssh_client.run_rails_command(
        "'MiqTask.delete_all; ConversionHost.delete_all'")
    if not delete_hosts.success:
        pytest.skip(
            f"Failed to delete all conversion hosts: {delete_hosts.output}")


def cleanup_target(provider, migrated_vm):
    """Helper function to cleanup instances and associated volumes from openstack"""
    if provider.one_of(OpenStackProvider):
        volumes = []
        vm = provider.mgmt.get_vm(migrated_vm.name)
        for vol in vm.raw._info['os-extended-volumes:volumes_attached']:
            volumes.append(vol['id'])
        migrated_vm.cleanup_on_provider()
        try:
            provider.mgmt.delete_volume(*volumes)
        except BadRequest as e:
            logger.warning(e)


def get_vm(request, appliance, source_provider, template_type, datastore='nfs'):
    """ Helper method that takes template , source provider and datastore
        and creates VM on source provider to migrate .

    Args:
        request
        appliance:
        source_provider: Provider on which vm is created
        template: Template used for creating VM
        datastore: datastore in which VM is created. If no datastore
                   is provided then by default VM is created on nfs datastore

        returns: Vm object
    """
    source_datastores_list = source_provider.data.get("datastores", [])
    source_datastore = [d.name for d in source_datastores_list if d.type == datastore][0]
    collection = source_provider.appliance.provider_based_collection(source_provider)
    vm_name = random_vm_name("v2v-auto")
    template = _get_template(source_provider, template_type)
    vm_obj = collection.instantiate(
        vm_name, source_provider, template_name=template.name
    )
    power_on_vm = True
    if 'win10' in template.name:
        # TODO Get the VM to the correct power state within the fixture/test, not here
        # the fixture or test
        # Need to leave this off, otherwise migration fails
        # because when migration process tries to power off the VM if it is powered off
        # and for win10, it hibernates and that state of filesystem is unsupported
        power_on_vm = False
    vm_obj.create_on_provider(
        timeout=2400,
        find_in_cfme=True,
        allow_skip="default",
        datastore=source_datastore,
        power_on=power_on_vm,
    )
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    return vm_obj


def get_data(provider, component, default_value):
    try:
        data = (provider.data.get(component, [])[0])
    except IndexError:
        data = default_value
    return data


def get_migrated_vm(src_vm_obj, target_provider):
    """Returns the migrated_vm from target_provider"""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm


def infra_mapping_default_data(source_provider, provider):
    """
    Default data for infrastructure mapping form.
    It is used in other methods to recursive update the data according
    to parameters in tests.

    Args:
        source_provider: Vmware provider
        provider: Target rhev/OSP provider
    """
    plan_type = VersionPicker({Version.lowest(): None,
                               "5.10": "rhv" if provider.one_of(RHEVMProvider) else "osp"}).pick()
    infra_mapping_data = {
        "name": fauxfactory.gen_alphanumeric(15, start="infra_map_"),
        "description": f"migration with vmware to {plan_type}",
        "plan_type": plan_type,
        "clusters": [component_generator("clusters", source_provider, provider)],
        "datastores": [component_generator(
            "datastores", source_provider, provider,
            get_data(source_provider, "datastores", "nfs").type,
            get_data(provider, "datastores", "nfs").type)],
        "networks": [
            component_generator("vlans", source_provider, provider,
                                get_data(source_provider, "vlans", "VM Network"),
                                get_data(provider, "vlans", "ovirtmgmt"))
        ],
    }
    return infra_mapping_data


@pytest.fixture(scope="function")
def mapping_data_vm_obj_mini(request, appliance, source_provider, provider):
    """Fixture to return minimal mapping data and vm object for migration plan"""
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    vm_obj = get_vm(request, appliance, source_provider, Templates.RHEL7_MINIMAL)

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping = infrastructure_mapping_collection.create(**infra_mapping_data)

    @request.addfinalizer
    def _cleanup():
        vm_obj.cleanup_on_provider()
        infrastructure_mapping_collection.delete(mapping)

    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


@pytest.fixture(scope="function")
def mapping_data_multiple_vm_obj_single_datastore(request, appliance, source_provider, provider,
                                                  source_type, dest_type, template_type):
    # this fixture will take list of N VM templates via request and call get_vm for each
    cluster = provider.data.get("clusters", [False])[0]
    if not cluster:
        pytest.skip("No data for cluster available on provider.")

    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Datastore migration of VM from {ds_type1} to {ds_type2},".format(
                ds_type1=source_type, ds_type2=dest_type
            ),
        },
    )
    vm_list = []
    for template_name in template_type:
        vm_list.append(get_vm(request, appliance, source_provider, template_name))
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=vm_list)


@pytest.fixture(scope="function")
def mapping_data_single_datastore(request, source_provider, provider,
                                  source_type, dest_type, template_type):
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Datastore migration of VM from {ds_type1} to {ds_type2},".format(
                ds_type1=source_type, ds_type2=dest_type
            ),
            "datastores": [
                component_generator(
                    "datastores", source_provider, provider, source_type, dest_type
                )
            ],
        },
    )
    return infra_mapping_data


@pytest.fixture(scope="function")
def mapping_data_single_network(request, source_provider, provider,
                                source_type, dest_type, template_type):
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Network migration of VM from {vlan1} to {vlan2},".format(
                vlan1=source_type, vlan2=dest_type
            ),
            "networks": [
                component_generator(
                    "vlans", source_provider, provider, source_type, dest_type
                )
            ],
        }
    )
    return infra_mapping_data


@pytest.fixture(scope="function")
def mapping_data_dual_vm_obj_dual_datastore(request, appliance, source_provider, provider):
    # Picking two datastores on Vmware and Target provider for this test
    source_type = dest_type = ['nfs', 'iscsi']

    vmware_nw = source_provider.data.get("vlans", [None])[0]
    rhvm_nw = provider.data.get("vlans", [None])[0]
    cluster = provider.data.get("clusters", [False])[0]
    if not vmware_nw or not rhvm_nw or not cluster:
        pytest.skip("No data for source or target network in providers.")

    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Dual DS migration of VM from {dss1} to {dst1},& from {dss2} to {dst2}".
            format(dss1=source_type[0],
                   dst1=source_type[1],
                   dss2=dest_type[0],
                   dst2=dest_type[1]),
            "datastores": [
                component_generator(
                    "datastores",
                    source_provider,
                    provider,
                    source_type[0],
                    source_type[1],
                ),
                component_generator(
                    "datastores",
                    source_provider,
                    provider,
                    dest_type[0],
                    dest_type[1],
                ),
            ],
            "networks": [
                component_generator(
                    "vlans",
                    source_provider,
                    provider,
                    source_provider.data.get("vlans")[0],
                    provider.data.get("vlans")[0],
                )
            ],
        },
    )
    # creating 2 VMs on two different datastores and returning its object list
    vm_obj1 = get_vm(request, appliance, source_provider, Templates.RHEL7_MINIMAL, source_type[0])
    vm_obj2 = get_vm(request, appliance, source_provider, Templates.RHEL7_MINIMAL, dest_type[0])
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj1, vm_obj2])


@pytest.fixture(scope="function")
def mapping_data_vm_obj_dual_nics(request, appliance, source_provider, provider):
    source_type = ["VM Network", "DPortGroup"]
    dest_type = ["ovirtmgmt", "Storage - VLAN 33"]

    vmware_nw = source_provider.data.get("vlans", [None])[0]
    rhvm_nw = provider.data.get("vlans", [None])[0]
    cluster = provider.data.get("clusters", [False])[0]
    if not vmware_nw or not rhvm_nw or not cluster:
        pytest.skip("No data for source or target network in providers.")

    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Dual DS migration of VM from {network1} to {network2}".format(
                network1=source_type, network2=dest_type),
            "networks": [
                component_generator(
                    "vlans", source_provider, provider, source_type[0], dest_type[0]),
                component_generator(
                    "vlans", source_provider, provider, source_type[1], dest_type[1])
            ]
        }
    )
    vm_obj = get_vm(request, appliance, source_provider, Templates.DUAL_NETWORK_TEMPLATE)
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


@pytest.fixture(scope="function")
def mapping_data_vm_obj_single_datastore(request, appliance, source_provider, provider,
                                         source_type, dest_type, template_type):
    """Return Infra Mapping form data and vm object"""
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single DS migration of VM from {ds_type1} to {ds_type2},".format(
                ds_type1=source_type, ds_type2=dest_type
            ),
            "datastores": [
                component_generator(
                    "datastores", source_provider, provider, source_type, dest_type
                )
            ],
        },
    )
    vm_obj = get_vm(request, appliance, source_provider, template_type, source_type)
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


@pytest.fixture(scope="function")
def mapping_data_vm_obj_single_network(request, appliance, source_provider, provider,
                                       source_type, dest_type, template_type):
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Network migration of VM from {vlan1} to {vlan2},".format(
                vlan1=source_type, vlan2=dest_type
            ),
            "networks": [
                component_generator(
                    "vlans", source_provider, provider, source_type, dest_type
                )
            ],
        },
    )
    vm_obj = get_vm(request, appliance, source_provider, template_type)
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


def component_generator(selector, source_provider, provider, source_type=None, target_type=None):
    """
    Component generator method to generate a dict of source and target
    components(clusters/datastores/networks).
    Gets the provider data based on selector from cfme_data.yaml and creates
    InfraMapping.component(source_list, target_list) object

    Test is skipped if no source or target data is found

    Args:
        selector: can be clusters/datastores/vlans
        source_provider: vmware provider to migrate from
        provider:  rhev or osp provider or target provider to migrate to
        source_type: string source datastores/networks on vmware provider to migrate from.
                     Ex: if source_type is "iscsi". Provider data is checked for datastore with type
                     iscsi and that datastores name is used.
        target_type: string target datastores/networks to migrate to

        returns : InfraMapping.component(source_list, target_list) object

    """

    if selector not in ['clusters', 'datastores', 'vlans']:
        raise ValueError("Please specify cluster, datastore or network(vlans) selector!")

    source_data = source_provider.data.get(selector, [])
    target_data = provider.data.get(selector, [])

    if not (source_data and target_data):
        pytest.skip("No source and target data")

    if selector == "clusters":
        sources = source_data or None
        targets = target_data or None
        component = InfraMapping.ClusterComponent(
            [partial_match(sources[0])], [partial_match(targets[0])]
        )
    elif selector == "datastores":
        # Ignoring target_type for osp and setting new value
        if provider.one_of(OpenStackProvider):
            target_type = "volume"

        sources = [d.name for d in source_data if d.type == source_type]
        targets = [d.name for d in target_data if d.type == target_type]
        component = InfraMapping.DatastoreComponent(
            [partial_match(sources[0])], [partial_match(targets[0])]
        )
    else:
        if provider.one_of(OpenStackProvider):
            # default lan for OSP
            target_type = "public"
        sources = [v for v in source_data if v == source_type]
        targets = [v for v in target_data if v == target_type]
        component = InfraMapping.NetworkComponent(
            [partial_match(sources[0])], [partial_match(targets[0])]
        )

    skip_test = not (sources and targets and component)
    if skip_test:
        pytest.skip(f"No data for source or target {selector} in providers.")
    return component
