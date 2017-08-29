# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest
from riggerlib import recursive_update

from textwrap import dedent

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.requests import Request
from utils import testgen
from utils.rest import assert_response
from utils.generators import random_vm_name
from utils.log import logger
from utils.update import update
from utils.version import current_version
from utils.wait import wait_for, RefreshTimer

pytestmark = [pytest.mark.meta(server_roles="+automate"),
              test_requirements.provision, pytest.mark.tier(2)]


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[['provisioning', 'image']], scope="function")


@pytest.yield_fixture(scope="function")
def testing_instance(request, setup_provider, provider, provisioning, vm_name):
    """ Fixture to prepare instance parameters for provisioning
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))

    instance = Instance.factory(vm_name, provider, image)

    inst_args = dict()

    # Base instance info
    inst_args['request'] = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
    }
    # TODO Move this into helpers on the provider classes
    recursive_update(inst_args, {'catalog': {'vm_name': vm_name}})

    # Check whether auto-selection of environment is passed
    try:
        auto = request.param
    except AttributeError:
        # in case nothing was passed just skip
        auto = False

    # All providers other than Azure
    if not provider.one_of(AzureProvider):
        recursive_update(inst_args, {
            'properties': {
                'instance_type': provisioning['instance_type'],
                'guest_keypair': provisioning['guest_keypair']},
            'environment': {
                'availability_zone': None if auto else provisioning['availability_zone'],
                'security_groups': None if auto else provisioning['security_group'],
                'automatic_placement': auto
            }
        })

    # Openstack specific
    if provider.one_of(OpenStackProvider):
        recursive_update(inst_args, {
            'environment': {
                'cloud_network': None if auto else provisioning['cloud_network']
            }
        })

    # GCE specific
    if provider.one_of(GCEProvider):
        recursive_update(inst_args, {
            'environment': {
                'cloud_network': None if auto else provisioning['cloud_network']
            },
            'properties': {
                'boot_disk_size': provisioning['boot_disk_size'],
                'is_preemptible': True if current_version() >= "5.7" else None}
        })

    # Azure specific
    if provider.one_of(AzureProvider):
        # Azure uses different provisioning keys for some reason
        recursive_update(inst_args, {
            'environment': {
                'automatic_placement': auto,
                'cloud_network': None if auto else provisioning['virtual_net'],
                'cloud_subnet': None if auto else provisioning['subnet_range'],
                'security_groups': None if auto else [provisioning['network_nsg']],
                'resource_groups': None if auto else provisioning['resource_group']
            },
            'properties': {
                'instance_type': provisioning['vm_size'].lower()},
            'customize': {
                'admin_username': provisioning['vm_user'],
                'admin_password': provisioning['vm_password']}})

    yield instance, inst_args, image

    try:
        if instance.does_vm_exist_on_provider():
            instance.delete_from_provider()
    except Exception as ex:
        logger.warning('Exception while deleting instance fixture, continuing: {}'
                       .format(ex.message))


@pytest.fixture(scope="function")
def vm_name(request):
    return random_vm_name('prov')


@pytest.mark.parametrize('testing_instance', [True, False], ids=["Auto", "Manual"], indirect=True)
def test_provision_from_template(provider, testing_instance, soft_assert):
    """ Tests instance provision from template

    Metadata:
        test_flag: provision
    """
    instance, inst_args, image = testing_instance
    instance.create(**inst_args)
    logger.info('Waiting for cfme provision request for vm %s', instance.name)
    request_description = 'Provision from [{}] to [{}]'.format(image, instance.name)
    provision_request = Request(request_description)
    try:
        provision_request.wait_for_request(method='ui')
    except Exception as e:
        logger.info("Provision failed {}: {}".format(e, provision_request.row.last_message.text()))
        raise e
    assert provision_request.is_succeeded(method='ui'), \
        "Provisioning failed with the message {}".format(provision_request.row.last_message.text)
    instance.wait_to_appear(timeout=800)
    provider.refresh_provider_relationships()
    logger.info("Refreshing provider relationships and power states")
    refresh_timer = RefreshTimer(time_for_refresh=300)
    wait_for(provider.is_refreshed,
             [refresh_timer],
             message="is_refreshed",
             num_sec=1000,
             delay=60,
             handle_exception=True)
    soft_assert(instance.does_vm_exist_on_provider(), "Instance wasn't provisioned")


@pytest.mark.uncollectif(lambda provider: not provider.one_of(GCEProvider) or
                         current_version() < "5.7")
def test_gce_preemtible_provision(provider, testing_instance, soft_assert):
    instance, inst_args, image = testing_instance
    instance.create(**inst_args)
    instance.wait_to_appear(timeout=800)
    provider.refresh_provider_relationships()
    logger.info("Refreshing provider relationships and power states")
    refresh_timer = RefreshTimer(time_for_refresh=300)
    wait_for(provider.is_refreshed,
             [refresh_timer],
             message="is_refreshed",
             num_sec=1000,
             delay=60,
             handle_exception=True)
    soft_assert('Yes' in instance.get_detail(
        properties=("Properties", "Preemptible")), "GCE Instance isn't Preemptible")
    soft_assert(instance.does_vm_exist_on_provider(), "Instance wasn't provisioned")


def test_provision_from_template_using_rest(
        appliance, request, setup_provider, provider, vm_name, provisioning):
    """ Tests provisioning from a template using the REST API.

    Metadata:
        test_flag: provision, rest
    """
    if 'flavors' not in appliance.rest_api.collections.all_names:
        pytest.skip("This appliance does not have `flavors` collection.")
    image_guid = appliance.rest_api.collections.templates.find_by(
        name=provisioning['image']['name'])[0].guid
    if ':' in provisioning['instance_type'] and provider.one_of(EC2Provider, GCEProvider):
        instance_type = provisioning['instance_type'].split(':')[0].strip()
    elif provider.type == 'azure':
        instance_type = provisioning['instance_type'].lower()
    else:
        instance_type = provisioning['instance_type']
    flavors = appliance.rest_api.collections.flavors.find_by(name=instance_type)
    assert flavors
    # TODO: Multi search when it works
    for flavor in flavors:
        if flavor.ems.name == provider.name:
            flavor_id = flavor.id
            break
    else:
        pytest.fail(
            "Cannot find flavour {} for provider {}".format(instance_type, provider.name))

    provision_data = {
        "version": "1.1",
        "template_fields": {
            "guid": image_guid,
        },
        "vm_fields": {
            "vm_name": vm_name,
            "instance_type": flavor_id,
            "request_type": "template",
        },
        "requester": {
            "user_name": "admin",
            "owner_first_name": "Administrator",
            "owner_last_name": "Administratorovich",
            "owner_email": "admin@example.com",
            "auto_approve": True,
        },
        "tags": {
        },
        "additional_values": {
        },
        "ems_custom_attributes": {
        },
        "miq_custom_attributes": {
        }
    }

    if not isinstance(provider, AzureProvider):
        provision_data['vm_fields']['availability_zone'] = provisioning['availability_zone']
        provision_data['vm_fields']['security_groups'] = [provisioning['security_group']]
        provision_data['vm_fields']['guest_keypair'] = provisioning['guest_keypair']

    if isinstance(provider, GCEProvider):
        provision_data['vm_fields']['cloud_network'] = provisioning['cloud_network']
        provision_data['vm_fields']['boot_disk_size'] = provisioning['boot_disk_size']
        provision_data['vm_fields']['zone'] = provisioning['availability_zone']
        provision_data['vm_fields']['region'] = 'us-central1'
    elif isinstance(provider, AzureProvider):
        # mapping: product/dialogs/miq_dialogs/miq_provision_azure_dialogs_template.yaml
        provision_data['vm_fields']['root_username'] = provisioning['vm_user']
        provision_data['vm_fields']['root_password'] = provisioning['vm_password']

    request.addfinalizer(
        lambda: provider.mgmt.delete_vm(vm_name) if provider.mgmt.does_vm_exist(vm_name) else None)

    request = appliance.rest_api.collections.provision_requests.action.create(**provision_data)[0]
    assert_response(appliance)

    def _finished():
        request.reload()
        if request.status.lower() in {"error"}:
            pytest.fail("Error when provisioning: `{}`".format(request.message))
        return request.request_state.lower() in {"finished", "provisioned"}

    wait_for(_finished, num_sec=3000, delay=10, message="REST provisioning finishes")
    wait_for(
        lambda: provider.mgmt.does_vm_exist(vm_name),
        num_sec=1000, delay=5, message="VM {} becomes visible".format(vm_name))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(EC2Provider, OpenStackProvider))
def test_manual_placement_using_rest(
        appliance, request, setup_provider, provider, vm_name, provisioning):
    """ Tests provisioning cloud instance with manual placement using the REST API.

    Metadata:
        test_flag: provision, rest
    """
    image_guid = appliance.rest_api.collections.templates.get(
        name=provisioning['image']['name']).guid
    provider_rest = appliance.rest_api.collections.providers.get(name=provider.name)
    security_group_name = provisioning['security_group'].split(':')[0].strip()
    if ':' in provisioning['instance_type'] and provider.one_of(EC2Provider):
        instance_type = provisioning['instance_type'].split(':')[0].strip()
    else:
        instance_type = provisioning['instance_type']

    flavors = appliance.rest_api.collections.flavors.find_by(name=instance_type)
    assert flavors
    flavor = None
    for flavor in flavors:
        if flavor.ems_id == provider_rest.id:
            break
    else:
        pytest.fail("Cannot find flavour.")

    provider_data = appliance.rest_api.get(provider_rest._href +
        '?attributes=cloud_networks,cloud_subnets,security_groups,cloud_tenants')

    # find out cloud network
    assert provider_data['cloud_networks']
    cloud_network_name = provisioning.get('cloud_network')
    cloud_network = None
    for cloud_network in provider_data['cloud_networks']:
        # If name of cloud network is available, find match.
        # Otherwise just "enabled" is enough.
        if cloud_network_name and cloud_network_name != cloud_network['name']:
            continue
        if cloud_network['enabled']:
            break
    else:
        pytest.fail("Cannot find cloud network.")

    # find out security group
    assert provider_data['security_groups']
    security_group = None
    for group in provider_data['security_groups']:
        if (group.get('cloud_network_id') == cloud_network['id'] and
                group['name'] == security_group_name):
            security_group = group
            break
        # OpenStack doesn't seem to have the "cloud_network_id" attribute.
        # At least try to find the group where the group name matches.
        elif not security_group and group['name'] == security_group_name:
            security_group = group
    if not security_group:
        pytest.fail("Cannot find security group.")

    # find out cloud subnet
    assert provider_data['cloud_subnets']
    cloud_subnet = None
    for cloud_subnet in provider_data['cloud_subnets']:
        if (cloud_subnet.get('cloud_network_id') == cloud_network['id'] and
                cloud_subnet['status'] in ('available', 'active')):
            break
    else:
        pytest.fail("Cannot find cloud subnet.")

    def _find_availability_zone_id():
        subnet_data = appliance.rest_api.get(provider_rest._href + '?attributes=cloud_subnets')
        for subnet in subnet_data['cloud_subnets']:
            if subnet['id'] == cloud_subnet['id'] and 'availability_zone_id' in subnet:
                return subnet['availability_zone_id']
        return False

    # find out availability zone
    availability_zone_id = None
    if provisioning.get('availability_zone'):
        availability_zone_entities = appliance.rest_api.collections.availability_zones.find_by(
            name=provisioning['availability_zone'])
        if availability_zone_entities and availability_zone_entities[0].ems_id == flavor.ems_id:
            availability_zone_id = availability_zone_entities[0].id
    if not availability_zone_id and 'availability_zone_id' in cloud_subnet:
        availability_zone_id = cloud_subnet['availability_zone_id']
    if not availability_zone_id:
        availability_zone_id, _ = wait_for(
            _find_availability_zone_id, num_sec=100, delay=5, message="availability_zone present")

    # find out cloud tenant
    cloud_tenant_id = None
    tenant_name = provisioning.get('cloud_tenant')
    if tenant_name:
        for tenant in provider_data.get('cloud_tenants', []):
            if (tenant['name'] == tenant_name and
                    tenant['enabled'] and
                    tenant['ems_id'] == flavor.ems_id):
                cloud_tenant_id = tenant['id']

    provision_data = {
        "version": "1.1",
        "template_fields": {
            "guid": image_guid
        },
        "vm_fields": {
            "vm_name": vm_name,
            "instance_type": flavor.id,
            "request_type": "template",
            "placement_auto": False,
            "cloud_network": cloud_network['id'],
            "cloud_subnet": cloud_subnet['id'],
            "placement_availability_zone": availability_zone_id,
            "security_groups": security_group['id'],
            "monitoring": "basic"
        },
        "requester": {
            "user_name": "admin",
            "owner_first_name": "Administrator",
            "owner_last_name": "Administratorovich",
            "owner_email": "admin@example.com",
            "auto_approve": True,
        },
        "tags": {
        },
        "additional_values": {
        },
        "ems_custom_attributes": {
        },
        "miq_custom_attributes": {
        }
    }
    if cloud_tenant_id:
        provision_data['vm_fields']['cloud_tenant'] = cloud_tenant_id

    request.addfinalizer(
        lambda: provider.mgmt.delete_vm(vm_name) if provider.mgmt.does_vm_exist(vm_name) else None)

    request = appliance.rest_api.collections.provision_requests.action.create(**provision_data)[0]
    assert_response(appliance)

    def _finished():
        request.reload()
        if 'error' in request.status.lower():
            pytest.fail("Error when provisioning: `{}`".format(request.message))
        return request.request_state.lower() in ('finished', 'provisioned')

    wait_for(_finished, num_sec=3000, delay=10, message="REST provisioning finishes")
    wait_for(
        lambda: provider.mgmt.does_vm_exist(vm_name),
        num_sec=1000, delay=5, message="VM {} becomes visible".format(vm_name))


VOLUME_METHOD = ("""
prov = $evm.root["miq_provision"]
prov.set_option(
    :clone_options,
    {{ :block_device_mapping => [{}] }})
""")

ONE_FIELD = """{{:volume_id => "{}", :device_name => "{}"}}"""


@pytest.fixture(scope="module")
def domain(request):
    domain = DomainCollection().create(name=fauxfactory.gen_alphanumeric(), enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    return domain


@pytest.fixture(scope="module")
def original_request_class():
    return DomainCollection().instantiate(name='ManageIQ')\
        .namespaces.instantiate(name='Cloud')\
        .namespaces.instantiate(name='VM')\
        .namespaces.instantiate(name='Provisioning')\
        .namespaces.instantiate(name='StateMachines')\
        .classes.instantiate(name='Methods')


@pytest.fixture(scope="module")
def modified_request_class(request, domain, original_request_class):
    original_request_class.copy_to(domain)
    klass = domain\
        .namespaces.instantiate(name='Cloud')\
        .namespaces.instantiate(name='VM')\
        .namespaces.instantiate(name='Provisioning')\
        .namespaces.instantiate(name='StateMachines')\
        .classes.instantiate(name='Methods')
    request.addfinalizer(klass.delete_if_exists)
    return klass


@pytest.fixture(scope="module")
def copy_domains(original_request_class, domain):
    methods = ['openstack_PreProvision', 'openstack_CustomizeRequest']
    for method in methods:
        original_request_class.methods.instantiate(name=method).copy_to(domain)


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[1152737])
@pytest.mark.parametrize("disks", [1, 2])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_provision_from_template_with_attached_disks(request, testing_instance, provider, disks,
                                                     soft_assert, domain, modified_request_class,
                                                     copy_domains, provisioning):
    """ Tests provisioning from a template and attaching disks

    Metadata:
        test_flag: provision
    """
    instance, inst_args, image = testing_instance
    # Modify availiability_zone for Azure provider
    if provider.one_of(AzureProvider):
        recursive_update(inst_args, {'environment': {'availability_zone': provisioning("av_set")}})

    device_name = "/dev/sd{}"
    device_mapping = []

    with provider.mgmt.with_volumes(1, n=disks) as volumes:
        for i, volume in enumerate(volumes):
            device_mapping.append((volume, device_name.format(chr(ord("b") + i))))
        # Set up automate

        method = modified_request_class.methods.instantiate(name="openstack_PreProvision")

        with update(method):
            disk_mapping = []
            for mapping in device_mapping:
                disk_mapping.append(ONE_FIELD.format(*mapping))
            method.script = VOLUME_METHOD.format(", ".join(disk_mapping))

        def _finish_method():
            with update(method):
                method.script = """prov = $evm.root["miq_provision"]"""
        request.addfinalizer(_finish_method)

        instance.create(**inst_args)

        for volume_id in volumes:
            soft_assert(vm_name in provider.mgmt.volume_attachments(volume_id))
        for volume, device in device_mapping:
            soft_assert(provider.mgmt.volume_attachments(volume)[vm_name] == device)
        instance.delete_from_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[1160342])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_provision_with_boot_volume(request, testing_instance, provider, soft_assert, copy_domains,
                                    modified_request_class):
    """ Tests provisioning from a template and attaching one booting volume.

    Metadata:
        test_flag: provision, volumes
    """
    instance, inst_args, image = testing_instance

    with provider.mgmt.with_volume(1, imageRef=provider.mgmt.get_template_id(image)) as volume:
        # Set up automate
        method = modified_request_class.methods.instantiate(name="openstack_CustomizeRequest")
        with update(method):
            method.script = dedent('''\
                $evm.root["miq_provision"].set_option(
                    :clone_options, {{
                        :image_ref => nil,
                        :block_device_mapping_v2 => [{{
                            :boot_index => 0,
                            :uuid => "{}",
                            :device_name => "vda",
                            :source_type => "volume",
                            :destination_type => "volume",
                            :delete_on_termination => false
                        }}]
                    }}
                )
            '''.format(volume))

        @request.addfinalizer
        def _finish_method():
            with update(method):
                method.script = """prov = $evm.root["miq_provision"]"""

        instance.create(**inst_args)

        soft_assert(vm_name in provider.mgmt.volume_attachments(volume))
        soft_assert(provider.mgmt.volume_attachments(volume)[vm_name] == "vda")
        instance.delete_from_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[1186413])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_provision_with_additional_volume(request, testing_instance, provider, soft_assert,
                                          copy_domains, domain, modified_request_class):
    """ Tests provisioning with setting specific image from AE and then also making it create and
    attach an additional 3G volume.

    Metadata:
        test_flag: provision, volumes
    """
    instance, inst_args, image = testing_instance

    # Set up automate
    method = modified_request_class.methods.instantiate(name="openstack_CustomizeRequest")
    try:
        image_id = provider.mgmt.get_template_id(provider.data["small_template"])
    except KeyError:
        pytest.skip("No small_template in provider adta!")
    with update(method):
        method.script = dedent('''\
            $evm.root["miq_provision"].set_option(
              :clone_options, {{
                :image_ref => nil,
                :block_device_mapping_v2 => [{{
                  :boot_index => 0,
                  :uuid => "{}",
                  :device_name => "vda",
                  :source_type => "image",
                  :destination_type => "volume",
                  :volume_size => 3,
                  :delete_on_termination => false
                }}]
              }}
        )
        '''.format(image_id))

    def _finish_method():
        with update(method):
            method.script = """prov = $evm.root["miq_provision"]"""
    request.addfinalizer(_finish_method)

    instance.create(**inst_args)

    prov_instance = provider.mgmt._find_instance_by_name(vm_name)
    try:
        assert hasattr(prov_instance, 'os-extended-volumes:volumes_attached')
        volumes_attached = getattr(prov_instance, 'os-extended-volumes:volumes_attached')
        assert len(volumes_attached) == 1
        volume_id = volumes_attached[0]["id"]
        assert provider.mgmt.volume_exists(volume_id)
        volume = provider.mgmt.get_volume(volume_id)
        assert volume.size == 3
    finally:
        instance.delete_from_provider()
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)
        if "volume_id" in locals():  # To handle the case of 1st or 2nd assert
            if provider.mgmt.volume_exists(volume_id):
                provider.mgmt.delete_volume(volume_id)
