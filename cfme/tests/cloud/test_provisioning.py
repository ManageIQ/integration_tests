# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest

from textwrap import dedent

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.cloud.instance import Instance
from cfme.cloud.instance.openstack import OpenStackInstance  # NOQA
from cfme.cloud.instance.ec2 import EC2Instance  # NOQA
from cfme.cloud.instance.azure import AzureInstance  # NOQA
from cfme.cloud.instance.gce import GCEInstance  # NOQA
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from utils import testgen
from utils.generators import random_vm_name
from utils.log import logger
from utils.update import update
from utils.version import current_version
from utils.wait import wait_for, RefreshTimer

pytestmark = [pytest.mark.meta(server_roles="+automate"),
              test_requirements.provision, pytest.mark.tier(2)]


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[['provisioning', 'image']], scope="function")


@pytest.fixture(scope="function")
def testing_instance(request, setup_provider, provider, provisioning, vm_name):
    """ Fixture to prepare instance parameters for provisioning
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))

    instance = Instance.factory(vm_name, provider, image)

    request.addfinalizer(instance.delete_from_provider)

    inst_args = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
    }
    if not isinstance(provider, AzureProvider):
        inst_args['instance_type'] = provisioning['instance_type']
        inst_args['availability_zone'] = provisioning['availability_zone']
        inst_args['security_groups'] = [provisioning['security_group']]
        inst_args['guest_keypair'] = provisioning['guest_keypair']

    if isinstance(provider, OpenStackProvider):
        inst_args['cloud_network'] = provisioning['cloud_network']

    if isinstance(provider, GCEProvider):
        inst_args['cloud_network'] = provisioning['cloud_network']
        inst_args['boot_disk_size'] = provisioning['boot_disk_size']
        inst_args['is_preemtible'] = True if current_version() >= "5.7" else None

    if isinstance(provider, AzureProvider):
        inst_args['cloud_network'] = provisioning['virtual_net']
        inst_args['cloud_subnet'] = provisioning['subnet_range']
        inst_args['security_groups'] = provisioning['network_nsg']
        inst_args['resource_groups'] = provisioning['resource_group']
        inst_args['instance_type'] = provisioning['vm_size'].lower()
        inst_args['admin_username'] = provisioning['vm_user']
        inst_args['admin_password'] = provisioning['vm_password']
    return instance, inst_args


@pytest.fixture(scope="function")
def vm_name(request, provider):
    return random_vm_name('prov')


def test_provision_from_template(request, setup_provider, provider, testing_instance, soft_assert):
    """ Tests instance provision from template

    Metadata:
        test_flag: provision
    """
    instance, inst_args = testing_instance
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
    soft_assert(instance.does_vm_exist_on_provider(), "Instance wasn't provisioned")


@pytest.mark.uncollectif(lambda provider: provider.type != 'gce' or current_version() < "5.7")
def test_gce_preemtible_provision(request, setup_provider, provider, testing_instance, soft_assert):
    instance, inst_args = testing_instance
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
        request, setup_provider, provider, vm_name, rest_api, provisioning):
    """ Tests provisioning from a template using the REST API.

    Metadata:
        test_flag: provision
    """
    if "flavors" not in rest_api.collections.all_names:
        pytest.skip("This appliance does not have `flavors` collection.")
    image_guid = rest_api.collections.templates.find_by(name=provisioning['image']['name'])[0].guid
    instance_type = (
        provisioning['instance_type'].split(":")[0].strip()
        if ":" in provisioning['instance_type'] and provider.type in ["ec2", "gce"]
        else provisioning['instance_type'])
    flavors = rest_api.collections.flavors.find_by(name=instance_type)
    assert len(flavors) > 0
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
            "availability_zone": provisioning["availability_zone"] if provider.type != "azure" else
            provisioning["av_set"],
            "security_groups": [provisioning["security_group"]],
            "guest_keypair": provisioning["guest_keypair"] if provider.type != "azure" else None
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

    if isinstance(provider, GCEProvider):
        provision_data['vm_fields']['cloud_network'] = provisioning['cloud_network']
        provision_data['vm_fields']['boot_disk_size'] = provisioning['boot_disk_size']
        provision_data['vm_fields']['zone'] = provisioning['availability_zone']
        provision_data['vm_fields']['region'] = 'us-central1'
    request.addfinalizer(
        lambda: provider.mgmt.delete_vm(vm_name) if provider.mgmt.does_vm_exist(vm_name) else None)
    request = rest_api.collections.provision_requests.action.create(**provision_data)[0]

    def _finished():
        request.reload()
        if request.status.lower() in {"error"}:
            pytest.fail("Error when provisioning: `{}`".format(request.message))
        return request.request_state.lower() in {"finished", "provisioned"}

    wait_for(_finished, num_sec=600, delay=5, message="REST provisioning finishes")
    wait_for(
        lambda: provider.mgmt.does_vm_exist(vm_name),
        num_sec=600, delay=5, message="VM {} becomes visible".format(vm_name))


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
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack')
def test_provision_from_template_with_attached_disks(
        request, setup_provider, provider, vm_name, provisioning,
        disks, soft_assert, domain, modified_request_class, copy_domains):
    """ Tests provisioning from a template and attaching disks

    Metadata:
        test_flag: provision
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))

    DEVICE_NAME = "/dev/sd{}"
    device_mapping = []

    with provider.mgmt.with_volumes(1, n=disks) as volumes:
        for i, volume in enumerate(volumes):
            device_mapping.append((volume, DEVICE_NAME.format(chr(ord("b") + i))))
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
        instance = Instance.factory(vm_name, provider, image)
        request.addfinalizer(instance.delete_from_provider)
        inst_args = {
            'email': 'image_provisioner@example.com',
            'first_name': 'Image',
            'last_name': 'Provisioner',
            'notes': note,
            'instance_type': provisioning['instance_type'],
            "availability_zone": provisioning["availability_zone"] if provider.type != "azure" else
            provisioning["av_set"],
            'security_groups': [provisioning['security_group']],
            'guest_keypair': provisioning['guest_keypair']
        }

        if isinstance(provider, OpenStackProvider):
            inst_args['cloud_network'] = provisioning['cloud_network']

        instance.create(**inst_args)

        for volume_id in volumes:
            soft_assert(vm_name in provider.mgmt.volume_attachments(volume_id))
        for volume, device in device_mapping:
            soft_assert(provider.mgmt.volume_attachments(volume)[vm_name] == device)
        instance.delete_from_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[1160342])
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack')
def test_provision_with_boot_volume(request, setup_provider, provider, vm_name,
        soft_assert, domain, copy_domains, provisioning, modified_request_class):
    """ Tests provisioning from a template and attaching one booting volume.

    Metadata:
        test_flag: provision, volumes
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))

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
        instance = Instance.factory(vm_name, provider, image)
        request.addfinalizer(instance.delete_from_provider)
        inst_args = {
            'email': 'image_provisioner@example.com',
            'first_name': 'Image',
            'last_name': 'Provisioner',
            'notes': note,
            'instance_type': provisioning['instance_type'],
            "availability_zone": provisioning["availability_zone"],
            'security_groups': [provisioning['security_group']],
            'guest_keypair': provisioning['guest_keypair']
        }

        if isinstance(provider, OpenStackProvider):
            inst_args['cloud_network'] = provisioning['cloud_network']

        instance.create(**inst_args)

        soft_assert(vm_name in provider.mgmt.volume_attachments(volume))
        soft_assert(provider.mgmt.volume_attachments(volume)[vm_name] == "vda")
        instance.delete_from_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[1186413])
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack')
def test_provision_with_additional_volume(request, setup_provider, provider, vm_name,
        soft_assert, copy_domains, domain, provisioning, modified_request_class):
    """ Tests provisioning with setting specific image from AE and then also making it create and
    attach an additional 3G volume.

    Metadata:
        test_flag: provision, volumes
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))

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
    instance = Instance.factory(vm_name, provider, image)
    request.addfinalizer(instance.delete_from_provider)
    inst_args = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
        'instance_type': provisioning['instance_type'],
        "availability_zone": provisioning["availability_zone"],
        'security_groups': [provisioning['security_group']],
        'guest_keypair': provisioning['guest_keypair']
    }

    if isinstance(provider, OpenStackProvider):
        inst_args['cloud_network'] = provisioning['cloud_network']

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
