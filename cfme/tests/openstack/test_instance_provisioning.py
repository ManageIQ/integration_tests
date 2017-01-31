# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest

from textwrap import dedent

from cfme import test_requirements
from cfme.automate import explorer as automate
from cfme.cloud.instance import Instance
from cfme.cloud.instance.openstack import OpenStackInstance  # NOQA
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from utils import testgen
from utils.generators import random_vm_name
from utils.log import logger
from utils.update import update
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
    if isinstance(provider, OpenStackProvider):
        inst_args['cloud_network'] = provisioning['cloud_network']

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
    domain = automate.Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="module")
def cls(request, domain):
    tcls = automate.Class(name="Methods",
        namespace=automate.Namespace.make_path("Cloud", "VM", "Provisioning", "StateMachines",
            parent=domain, create_on_init=True))
    tcls.create()
    request.addfinalizer(lambda: tcls.delete() if tcls.exists() else None)
    return tcls


@pytest.fixture(scope="module")
def copy_domains(domain):
    methods = ['openstack_PreProvision', 'openstack_CustomizeRequest']
    for method in methods:
        ocls = automate.Class(name="Methods",
            namespace=automate.Namespace.make_path("Cloud", "VM", "Provisioning", "StateMachines",
                parent=automate.Domain(name="ManageIQ (Locked)")))

        method = automate.Method(name=method, cls=ocls)

        method = method.copy_to(domain)


@pytest.mark.meta(blockers=[1186413])
@pytest.mark.uncollectif(lambda provider: provider.type != 'openstack')
def test_provision_with_additional_volume(request, setup_provider, provider, vm_name,
        soft_assert, copy_domains, domain, provisioning):
    """ Tests provisioning with setting specific image from AE and then also making it create and
    attach an additional 3G volume.

    Metadata:
        test_flag: provision, volumes
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))

    # Set up automate
    cls = automate.Class(
        name="Methods",
        namespace=automate.Namespace.make_path("Cloud", "VM", "Provisioning", "StateMachines",
            parent=domain))
    method = automate.Method(
        name="openstack_CustomizeRequest",
        cls=cls)
    try:
        image_id = provider.mgmt.get_template_id(provider.data["small_template"])
    except KeyError:
        pytest.skip("No small_template in provider adta!")
    with update(method):
        method.data = dedent('''\
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
            method.data = """prov = $evm.root["miq_provision"]"""
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
