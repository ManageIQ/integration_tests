import tempfile
from collections import namedtuple

import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import rhel7_minimal
from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import conf
from cfme.utils import ssh
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from cfme.v2v.infrastructure_mapping import InfrastructureMapping as InfraMapping


FormDataVmObj = namedtuple("FormDataVmObj", ["infra_mapping_data", "vm_list"])
V2vProviders = namedtuple("V2vProviders", ["vmware_provider", "rhv_provider", "osp_provider"])


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
            osp_provider = v2v_provider
            setup_or_skip(request, osp_provider)
        else:
            pytest.skip("Provider {} is not a valid provider for v2v tests".format(provider.name))
    v2v_providers = V2vProviders(vmware_provider=vmware_provider,
                                 rhv_provider=rhv_provider,
                                 osp_provider=osp_provider)

    # Transformation method can be vddk or ssh
    if hasattr(request, "param") and request.param == "SSH":
        transformation_method = "SSH"
    else:
        transformation_method = "VDDK"

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
    rhv_hosts = None

    if v2v_providers.rhv_provider is not None:
        rhv_hosts = v2v_providers.rhv_provider.hosts.all()
        provider_list.append(v2v_providers.rhv_provider)

    try:
        for v2v_provider in provider_list:
            hosts = v2v_provider.hosts.all()
            for host in hosts:
                host_data = [data for data in v2v_provider.data['hosts']
                             if data['name'] == host.name]
                if not host_data:
                    pytest.skip("No host data")
                host.update_credentials_rest(credentials=host_data[0]['credentials'])
    except Exception:
        logger.exception("Exception when trying to add the host credentials.")
        pytest.skip("No data for hosts in providers, failed to retrieve hosts and add creds.")
    # Configure conversion host for RHEV migration
    if rhv_hosts is not None:
        __set_conversion_instance_for_rhev_ui(appliance,
                                              v2v_providers.vmware_provider,
                                              v2v_providers.rhv_provider, rhv_hosts,
                                              transformation_method)
    if v2v_providers.osp_provider is not None:
        __set_conversion_instance_for_osp_ui(appliance,
                                             v2v_providers.vmware_provider,
                                             v2v_providers.osp_provider,
                                             transformation_method)


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


def __vddk_url(): # noqa
    """Get vddk url from cfme_data"""
    vddk_version = "v2v_vddk"
    try:
        vddk_urls = conf.cfme_data.basic_info.vddk_url
    except (KeyError, AttributeError):
        pytest.skip("VDDK URLs not found in cfme_data.basic_info")
    url = vddk_urls.get(vddk_version)

    if url is None:
        pytest.skip("VDDK {} is unavailable, skipping test".format(vddk_version))
    return url


def __configure_conversion_host_ui(appliance, target_provider, hostname, default,  # noqa
                                   conv_host_key, transformation_method,
                                   vmware_ssh_key, osp_cert_switch=None, osp_ca_cert=None):

    conv_host_collection = appliance.collections.v2v_conversion_hosts
    conv_host = conv_host_collection.create(
        target_provider=target_provider,
        cluster=get_data(target_provider, "clusters", default),
        hostname=hostname,
        conv_host_key=conv_host_key,
        transformation_method=transformation_method,
        vddk_library_path=__vddk_url(),
        vmware_ssh_key=vmware_ssh_key,
        osp_cert_switch=osp_cert_switch,
        osp_ca_cert=osp_ca_cert
    )
    if not conv_host.is_host_configured:
        pytest.skip("Failed to set conversion host/instance: {}".format(hostname))


def __set_conversion_instance_for_rhev_ui(appliance, source_provider,  # noqa
                                          target_provider, rhev_hosts,
                                          transformation_method):
    """
    Args:
        appliance:
        source_provider: Vmware
        target_provider : RHEV
        transformation_method : vddk or ssh as per test requirement
        rhev_hosts: hosts in rhev to configure for conversion
    """
    # Delete all prior conversion hosts otherwise it creates duplicate entries
    delete_hosts = appliance.ssh_client.run_rails_command("ConversionHost.delete_all")
    if not delete_hosts.success:
        pytest.skip("Failed to delete all conversion hosts:".format(delete_hosts.output))

    # Fetch Vmware Key
    vmware_ssh_key = None
    if transformation_method == "SSH":
        ssh_key_name = source_provider.data['private-keys']['vmware-ssh-key']['credentials']
        vmware_ssh_key = conf.credentials[ssh_key_name]['password']

    # Get rhev rsa key from rhevm
    credential = conf.credentials[target_provider.data["ssh_creds"]]
    ssh_client = ssh.SSHClient(
        hostname=target_provider.hostname,
        username=credential.username,
        password=credential.password,
    )
    private_key = ssh_client.run_command("cat /etc/pki/ovirt-engine/keys/engine_id_rsa").output
    temp_file = tempfile.NamedTemporaryFile('w')
    with open(temp_file.name, 'w') as f:
        f.write(private_key)
    conv_host_key = temp_file.name

    for host in rhev_hosts:
        __configure_conversion_host_ui(appliance,
                                       target_provider, host.name, "Default",
                                       conv_host_key, transformation_method,
                                       vmware_ssh_key)


def __set_conversion_instance_for_osp_ui(appliance, source_provider,  # noqa
                                         osp_provider, transformation_method):
    """
    Args:
        appliance:
        source_provider: Vmware
        osp_provider: OSP
        transformation_method: vddk or ssh
    """

    # Delete all prior conversion hosts otherwise it creates duplicate entries
    delete_hosts = appliance.ssh_client.run_rails_command("'ConversionHost.delete_all'")
    if not delete_hosts.success:
        pytest.skip("Failed to delete all conversion hosts:".format(delete_hosts.output))

    # transformation method needs to be lower case always
    trans_method = transformation_method.lower()
    try:
        conversion_instances = osp_provider.data['conversion_instances'][trans_method]
    except KeyError:
        pytest.skip("No conversion instance on provider.")

    vmware_ssh_key = None
    if transformation_method == "SSH":
        ssh_key_name = source_provider.data['private-keys']['vmware-ssh-key']['credentials']
        vmware_ssh_key = conf.credentials[ssh_key_name]['password']

    osp_key_name = osp_provider.data['private-keys']['conversion_host_ssh_key']['credentials']
    key_value = conf.credentials[osp_key_name]['password']
    temp_file = tempfile.NamedTemporaryFile('w')
    with open(temp_file.name, 'w') as f:
        f.write(key_value)
    conv_host_key = temp_file.name

    tls_key_name = osp_provider.data['private-keys']['tls_cert']['credentials']
    tls_cert_key = conf.credentials[tls_key_name]['password']

    for instance in conversion_instances:
        __configure_conversion_host_ui(appliance,
                                       osp_provider, instance, "admin",
                                       conv_host_key, transformation_method,
                                       vmware_ssh_key, osp_cert_switch=True,
                                       osp_ca_cert=tls_cert_key)


def get_vm(request, appliance, source_provider, template, datastore='nfs'):
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
    vm_obj = collection.instantiate(
        vm_name, source_provider, template_name=template(source_provider)["name"]
    )
    power_on_vm = True
    if template.__name__ == "win10_template":
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
        "name": "infra_map_{}".format(fauxfactory.gen_alphanumeric()),
        "description": "migration with vmware to {}".format(plan_type),
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
    vm_obj = get_vm(request, appliance, source_provider, template=rhel7_minimal)

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping = infrastructure_mapping_collection.create(**infra_mapping_data)

    @request.addfinalizer
    def _cleanup():
        vm_obj.cleanup_on_provider()
        infrastructure_mapping_collection.delete(mapping)

    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


@pytest.fixture(scope="function")
def mapping_data_multiple_vm_obj_single_datastore(request, appliance, source_provider, provider):
    # this fixture will take list of N VM templates via request and call get_vm for each
    cluster = provider.data.get("clusters", [False])[0]
    if not cluster:
        pytest.skip("No data for cluster available on provider.")

    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Datastore migration of VM from {ds_type1} to {ds_type2},".format(
                ds_type1=request.param[0], ds_type2=request.param[1]
            ),
            "networks": [
                component_generator("vlans", source_provider, provider, "VM Network", "ovirtmgmt")
            ],
        },
    )
    vm_list = []
    for template_name in request.param[2]:
        vm_list.append(get_vm(request, appliance, source_provider, template_name))
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=vm_list)


@pytest.fixture(scope="function")
def mapping_data_single_datastore(request, source_provider, provider):
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Datastore migration of VM from {ds_type1} to {ds_type2},".format(
                ds_type1=request.param[0], ds_type2=request.param[1]
            ),
            "datastores": [
                component_generator(
                    "datastores", source_provider, provider, request.param[0], request.param[1]
                )
            ],
        },
    )
    return infra_mapping_data


@pytest.fixture(scope="function")
def mapping_data_single_network(request, source_provider, provider):
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Network migration of VM from {vlan1} to {vlan2},".format(
                vlan1=request.param[0], vlan2=request.param[1]
            ),
            "networks": [
                component_generator(
                    "vlans", source_provider, provider, request.param[0], request.param[1]
                )
            ],
        }
    )
    return infra_mapping_data


@pytest.fixture(scope="function")
def mapping_data_dual_vm_obj_dual_datastore(request, appliance, source_provider, provider):
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
            format(dss1=request.param[0][0],
                   dst1=request.param[0][1],
                   dss2=request.param[1][0],
                   dst2=request.param[1][1]),
            "datastores": [
                component_generator(
                    "datastores",
                    source_provider,
                    provider,
                    request.param[0][0],
                    request.param[0][1],
                ),
                component_generator(
                    "datastores",
                    source_provider,
                    provider,
                    request.param[1][0],
                    request.param[1][1],
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
    vm_obj1 = get_vm(request, appliance, source_provider, request.param[0][2], request.param[0][0])
    vm_obj2 = get_vm(request, appliance, source_provider, request.param[1][2], request.param[1][0])
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj1, vm_obj2])


@pytest.fixture(scope="function")
def mapping_data_vm_obj_dual_nics(request, appliance, source_provider, provider):
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
            format(dss1=request.param[0][0],
                   dst1=request.param[0][1],
                   dss2=request.param[1][0],
                   dst2=request.param[1][1]),
            "networks": [
                component_generator(
                    "vlans", source_provider, provider, request.param[0][0], request.param[0][1]
                ),
                component_generator(
                    "vlans", source_provider, provider, request.param[1][0], request.param[1][1]
                ),
            ],
        },
    )
    vm_obj = get_vm(request, appliance, source_provider, request.param[2])
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


@pytest.fixture(scope="function")
def mapping_data_vm_obj_single_datastore(request, appliance, source_provider, provider):
    """Return Infra Mapping form data and vm object"""
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single DS migration of VM from {ds_type1} to {ds_type2},".format(
                ds_type1=request.param[0], ds_type2=request.param[1]
            ),
            "datastores": [
                component_generator(
                    "datastores", source_provider, provider, request.param[0], request.param[1]
                )
            ],
        },
    )
    vm_obj = get_vm(request, appliance, source_provider, request.param[2], request.param[0])
    return FormDataVmObj(infra_mapping_data=infra_mapping_data, vm_list=[vm_obj])


@pytest.fixture(scope="function")
def mapping_data_vm_obj_single_network(request, appliance, source_provider, provider):
    infra_mapping_data = infra_mapping_default_data(source_provider, provider)
    recursive_update(
        infra_mapping_data,
        {
            "description": "Single Network migration of VM from {vlan1} to {vlan2},".format(
                vlan1=request.param[0], vlan2=request.param[1]
            ),
            "networks": [
                component_generator(
                    "vlans", source_provider, provider, request.param[0], request.param[1]
                )
            ],
        },
    )
    vm_obj = get_vm(request, appliance, source_provider, request.param[2])
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
        sources = [v for v in source_data if v == source_type]
        targets = [v for v in target_data if v == target_type]
        component = InfraMapping.NetworkComponent(
            [partial_match(sources[0])], [partial_match(targets[0])]
        )

    skip_test = not (sources and targets and component)
    if skip_test:
        pytest.skip("No data for source or target {} in providers.".format(selector))
    return component
