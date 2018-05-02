# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
from textwrap import dedent

import pytest
import fauxfactory
from riggerlib import recursive_update
from widgetastic_patternfly import CheckableBootstrapTreeview as Check_tree

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.vm import VM
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.wait import wait_for

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
    instance = Instance.factory(vm_name, provider, image)

    inst_args = instance.vm_default_args
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

    if auto:
        inst_args['environment'] = {'automatic_placement': auto}
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
    instance, inst_args, _ = testing_instance
    instance.create(check_existing=True, provisioning_data=inst_args, find_in_cfme=True)
    return instance


@pytest.mark.parametrize('testing_instance', [True, False], ids=["Auto", "Manual"], indirect=True)
def test_cloud_provision_from_template(provider, provisioned_instance, setup_provider):
    """ Tests instance provision from template

    Metadata:
        test_flag: provision
    """
    assert provisioned_instance.does_vm_exist_on_provider(), "Instance wasn't provisioned"


@pytest.mark.uncollectif(lambda provider: not provider.one_of(GCEProvider))
def test_gce_preemptible_provision(provider, testing_instance):
    instance, inst_args, image = testing_instance
    recursive_update(inst_args, {'properties': {'is_preemptible': True}})
    instance.create(check_existing=True, provisioning_data=inst_args, find_in_cfme=True)
    view = navigate_to(instance, "Details")
    preemptible = view.entities.summary("Properties").get_text_of("Preemptible")
    assert 'Yes' in preemptible, "GCE Instance isn't Preemptible"


@pytest.mark.parametrize('auto', [True, False], ids=["Auto", "Manual"])
def test_cloud_provision_from_template_using_rest(
        appliance, request, setup_provider, provider, vm_name, provisioning, auto):
    """ Tests provisioning from a template using the REST API

    Metadata:
        test_flag: provision, rest
    """
    vm = VM.factory(vm_name, provider)
    request.addfinalizer(
        lambda: vm.cleanup_on_provider()
    )
    inst_args = vm.vm_default_args_rest
    if auto:
        # Making sure that we don't pass mandatory fields. Add new if needed
        for key in ['cloud_network', 'cloud_subnet', 'placement_availability_zone']:
            del inst_args['vm_fields'][key]
        recursive_update(inst_args, {"additional_values": {"placement_auto": True}})
    assert vm.create_rest(provisioning_data=inst_args), "VM {} wasn't created".format(vm.name)


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
    with pytest.raises(Exception, match="error: Error during 'Automate Class copy'"):
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


@pytest.mark.parametrize("disks", [1, 2])
@pytest.mark.uncollectif(lambda provider: not provider.one_of(OpenStackProvider))
def test_cloud_provision_from_template_with_attached_disks(
        request, testing_instance, provider, disks,
        soft_assert, domain, modified_request_class,
        copy_domains, provisioning):
    """ Tests provisioning from a template and attaching disks

    Metadata:
        test_flag: provision
    """
    instance, inst_args, image = testing_instance

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

        instance.create(provisioning_data=inst_args)

        for volume_id in volumes:
            soft_assert(vm_name in provider.mgmt.volume_attachments(volume_id))
        for volume, device in device_mapping:
            soft_assert(provider.mgmt.volume_attachments(volume)[vm_name] == device)
        instance.cleanup_on_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.does_vm_exist_on_provider(), num_sec=180, delay=5)


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

        instance.create(provisioning_data=inst_args)

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

    instance.create(provisioning_data=inst_args)

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
        instance.cleanup_on_provider()
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
