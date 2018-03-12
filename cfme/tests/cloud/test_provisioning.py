# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest

from riggerlib import recursive_update
from textwrap import dedent
from widgetastic.utils import partial_match
from widgetastic_patternfly import CheckableBootstrapTreeview as Check_tree

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.vm import VM
from cfme.utils import error
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.rest import assert_response
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.wait import wait_for, RefreshTimer


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.provision, pytest.mark.tier(2),
    pytest.mark.provider(
        [CloudProvider], required_fields=[['provisioning', 'image']], scope="function"
    )
]


@pytest.fixture()
def vm_name():
    return random_vm_name(context='prov')


@pytest.fixture()
def testing_instance(request, setup_provider, provider, provisioning, vm_name, tag):
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
    auto = False  # By default provisioning will be manual
    try:
        parameter = request.param
        if parameter == 'tag':
            inst_args['purpose'] = {
                'apply_tags': Check_tree.CheckNode(
                    ['{} *'.format(tag.category.display_name), tag.display_name])
            }
        else:
            auto = parameter
    except AttributeError:
        # in case nothing was passed just skip
        pass

    recursive_update(inst_args, {
        'environment': {
            'availability_zone': provisioning.get('availability_zone', None),
            'security_groups': [provisioning.get('security_group', None)],
            'cloud_network': provisioning.get('cloud_network', None),
            'cloud_subnet': provisioning.get('cloud_subnet', None),
            'resource_groups': provisioning.get('resource_group', None)
        },
        'properties': {
            'instance_type': partial_match(provisioning.get('instance_type', None)),
            'guest_keypair': provisioning.get('guest_keypair', None)}
    })
    # GCE specific
    if provider.one_of(GCEProvider):
        recursive_update(inst_args, {
            'properties': {
                'boot_disk_size': provisioning['boot_disk_size'],
                'is_preemptible': True}
        })

    # Azure specific
    if provider.one_of(AzureProvider):
        # Azure uses different provisioning keys for some reason
        try:
            template = provider.data.templates.small_template
            vm_user = credentials[template.creds].username
            vm_password = credentials[template.creds].password
        except AttributeError:
            pytest.skip('Could not find small_template or credentials for {}'.format(provider.name))
        recursive_update(inst_args, {
            'customize': {
                'admin_username': vm_user,
                'root_password': vm_password}})
    if auto:
        inst_args.update({'environment': {'automatic_placement': auto}})
    yield instance, inst_args, image

    logger.info('Fixture cleanup, deleting test instance: %s', instance.name)
    try:
        instance.cleanup_on_provider()
    except Exception as ex:
        logger.warning('Exception while deleting instance fixture, continuing: {}'
                       .format(ex.message))


@pytest.fixture(scope='function')
def provisioned_instance(provider, testing_instance, appliance):
    """ Checks provisioning status for instance """
    instance, inst_args, image = testing_instance
    instance.create(**inst_args)
    logger.info('Waiting for cfme provision request for vm %s', instance.name)
    request_description = 'Provision from [{}] to [{}]'.format(image, instance.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    try:
        provision_request.wait_for_request(method='ui')
    except Exception as e:
        logger.info(
            "Provision failed {}: {}".format(e, provision_request.request_state))
        raise e
    assert provision_request.is_succeeded(method='ui'), (
        "Provisioning failed with the message {}".format(
            provision_request.row.last_message.text))
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
    return instance


@pytest.mark.parametrize('testing_instance', [True, False], ids=["Auto", "Manual"], indirect=True)
def test_provision_from_template(provider, provisioned_instance):
    """ Tests instance provision from template

    Metadata:
        test_flag: provision
    """
    assert provisioned_instance.does_vm_exist_on_provider(), "Instance wasn't provisioned"


@pytest.mark.uncollectif(lambda provider: not provider.one_of(GCEProvider))
def test_gce_preemptible_provision(provider, testing_instance, soft_assert):
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
    view = navigate_to(instance, "Details")
    preemptible = view.entities.summary("Properties").get_text_of("Preemptible")
    soft_assert('Yes' in preemptible, "GCE Instance isn't Preemptible")
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
        recursive_update(provision_data, {
                         'vm_fields': {
                             'availability_zone': provisioning['availability_zone'],
                             'security_groups': [provisioning['security_group']],
                             'guest_keypair': provisioning['guest_keypair']}})
    if isinstance(provider, GCEProvider):
        recursive_update(provision_data, {
                         'vm_fields': {
                             'cloud_network': provisioning['cloud_network'],
                             'boot_disk_size': provisioning['boot_disk_size'].replace(' ', '.'),
                             'zone': provisioning['availability_zone'],
                             'region': provider.data["region"]}})
    elif isinstance(provider, AzureProvider):
        try:
            template = provider.data.templates.small_template
            vm_user = credentials[template.creds].username
            vm_password = credentials[template.creds].password
        except AttributeError:
            pytest.skip('Could not find small_template or credentials for {}'.format(provider.name))
        # mapping: product/dialogs/miq_dialogs/miq_provision_azure_dialogs_template.yaml
        recursive_update(provision_data, {
                         'vm_fields': {
                             'root_username': vm_user,
                             'root_password': vm_password}})

    request.addfinalizer(
        lambda: VM.factory(vm_name, provider).cleanup_on_provider()
    )

    response = appliance.rest_api.collections.provision_requests.action.create(**provision_data)[0]
    assert_response(appliance)

    provision_request = appliance.collections.requests.instantiate(description=response.description)

    provision_request.wait_for_request()
    assert provision_request.is_succeeded(), ("Provisioning failed with the message {}".format(
        provision_request.rest.message))

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
    cloud_network_name = provisioning.get('cloud_network').strip()
    if provider.one_of(EC2Provider):
        cloud_network_name = cloud_network_name.split()[0]
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
        lambda: VM.factory(vm_name, provider).cleanup_on_provider()
    )

    response = appliance.rest_api.collections.provision_requests.action.create(**provision_data)[0]
    assert_response(appliance)

    provision_request = appliance.collections.requests.instantiate(description=response.description)

    provision_request.wait_for_request()
    assert provision_request.is_succeeded(), ("Provisioning failed with the message {}".format(
        provision_request.rest.message))

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
def domain(request, appliance):
    domain = DomainCollection(appliance).create(name=fauxfactory.gen_alphanumeric(), enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    return domain


@pytest.fixture(scope="module")
def original_request_class(appliance):
    return DomainCollection(appliance).instantiate(name='ManageIQ')\
        .namespaces.instantiate(name='Cloud')\
        .namespaces.instantiate(name='VM')\
        .namespaces.instantiate(name='Provisioning')\
        .namespaces.instantiate(name='StateMachines')\
        .classes.instantiate(name='Methods')


@pytest.fixture(scope="module")
def modified_request_class(request, domain, original_request_class):
    with error.handler("error: Error during 'Automate Class copy'"):
        # methods of this class might have been copied by other fixture, so this error can occur
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
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_provision_with_boot_volume(request, testing_instance, provider, soft_assert,
                                    modified_request_class, appliance, copy_domains):
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
                            :volume_size => 1,
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

        request_description = 'Provision from [{}] to [{}]'.format(image,
                                                                   instance.name)
        provision_request = appliance.collections.requests.instantiate(request_description)
        try:
            provision_request.wait_for_request(method='ui')
        except Exception as e:
            logger.info(
                "Provision failed {}: {}".format(e, provision_request.request_state))
            raise e
        msg = "Provisioning failed with the message {}".format(
            provision_request.row.last_message.text)
        assert provision_request.is_succeeded(method='ui'), msg
        soft_assert(instance.name in provider.mgmt.volume_attachments(volume))
        soft_assert(provider.mgmt.volume_attachments(volume)[instance.name] == "/dev/vda")
        instance.delete_from_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)


# Not collected for EC2 in generate_tests above
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_provision_with_additional_volume(request, testing_instance, provider, small_template,
                                          soft_assert, modified_request_class, appliance,
                                          copy_domains):
    """ Tests provisioning with setting specific image from AE and then also making it create and
    attach an additional 3G volume.

    Metadata:
        test_flag: provision, volumes
    """
    instance, inst_args, image = testing_instance

    # Set up automate
    method = modified_request_class.methods.instantiate(name="openstack_CustomizeRequest")
    try:
        image_id = provider.mgmt.get_template_id(small_template.name)
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

    request_description = 'Provision from [{}] to [{}]'.format(small_template.name, instance.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    try:
        provision_request.wait_for_request(method='ui')
    except Exception as e:
        logger.info(
            "Provision failed {}: {}".format(e, provision_request.request_state))
        raise e
    assert provision_request.is_succeeded(method='ui'), (
        "Provisioning failed with the message {}".format(
            provision_request.row.last_message.text))

    prov_instance = provider.mgmt._find_instance_by_name(instance.name)
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


@pytest.mark.parametrize('testing_instance', ['tag'], indirect=True)
def test_cloud_provision_with_tag(provisioned_instance, tag):
    """ Tests tagging instance using provisioning dialogs.

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, pick a tag.
        * Submit the provisioning request and wait for it to finish.
        * Visit instance page, it should display the selected tags
    Metadata:
        test_flag: provision
    """
    assert provisioned_instance.does_vm_exist_on_provider(), "Instance wasn't provisioned"
    tags = provisioned_instance.get_tags()
    assert any(
        instance_tag.category.display_name == tag.category.display_name and
        instance_tag.display_name == tag.display_name for instance_tag in tags), (
        "{}: {} not in ({})".format(tag.category.display_name, tag.display_name, str(tags)))
