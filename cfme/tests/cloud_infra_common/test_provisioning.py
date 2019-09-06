# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
from textwrap import dedent

import pytest
from riggerlib import recursive_update
from widgetastic_patternfly import CheckableBootstrapTreeview as Check_tree

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils import normalize_text
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    test_requirements.provision,
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers,
                         filters=[ProviderFilter(classes=[CloudProvider, InfraProvider],
                                                 required_flags=['provision'])],
                         scope="function"),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture()
def vm_name():
    return random_vm_name(context='prov', max_length=12)


@pytest.fixture()
def instance_args(request, provider, provisioning, vm_name):
    """ Fixture to prepare instance parameters for provisioning
    """
    inst_args = dict(template_name=provisioning.get('image', {}).get('name') or provisioning.get(
        'template'))
    if not inst_args.get('template_name'):
        pytest.skip(reason='template name not specified in the provisioning in config')

    # Base instance info
    inst_args['request'] = {
        'notes': 'Testing provisioning from image {} to vm {} on provider {}'
                 .format(inst_args.get('template_name'), vm_name, provider.key),
    }
    # Check whether auto-selection of environment is passed
    auto = False  # By default provisioning will be manual
    try:
        parameter = request.param
        auto = parameter
    except AttributeError:
        # in case nothing was passed just skip
        pass

    if auto:
        inst_args.update({'environment': {'automatic_placement': auto}})
    yield vm_name, inst_args


@pytest.fixture
def provisioned_instance(provider, instance_args, appliance):
    """ Checks provisioning status for instance """
    vm_name, inst_args = instance_args
    collection = appliance.provider_based_collection(provider)
    instance = collection.create(vm_name, provider, form_values=inst_args)
    if not instance:
        raise Exception("instance returned by collection.create is 'None'")
    yield instance

    logger.info('Instance cleanup, deleting %s', instance.name)
    try:
        instance.cleanup_on_provider()
    except Exception as ex:
        logger.warning('Exception while deleting instance fixture, continuing: {}'
                       .format(ex.message))


@pytest.mark.rhel_testing
@pytest.mark.parametrize('instance_args', [True, False], ids=["Auto", "Manual"], indirect=True)
def test_provision_from_template(provider, provisioned_instance):
    """ Tests instance provision from template via CFME UI

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    assert provisioned_instance.exists_on_provider, "Instance wasn't provisioned successfully"


@pytest.mark.provider([GCEProvider], required_fields=[['provisioning', 'image']],
                      override=True)
@pytest.mark.usefixtures('setup_provider')
def test_gce_preemptible_provision(appliance, provider, instance_args, soft_assert):
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/6h
    """
    vm_name, inst_args = instance_args
    inst_args['properties']['is_preemptible'] = True
    instance = appliance.collections.cloud_instances.create(vm_name,
                                                            provider,
                                                            form_values=inst_args)
    view = navigate_to(instance, "Details")
    preemptible = view.entities.summary("Properties").get_text_of("Preemptible")
    soft_assert('Yes' in preemptible, "GCE Instance isn't Preemptible")
    soft_assert(instance.exists_on_provider, "Instance wasn't provisioned successfully")


@pytest.mark.rhv2
@pytest.mark.meta(automates=[1472844])
@pytest.mark.parametrize("edit", [True, False], ids=["edit", "approve"])
def test_provision_approval(appliance, provider, vm_name, smtp_test, request,
                            edit, soft_assert):
    """ Tests provisioning approval. Tests couple of things.

    * Approve manually
    * Approve by editing the request to conform

    Prerequisities:
        * A provider that can provision.
        * Automate role enabled
        * User with e-mail set so you can receive and view them

    Steps:
        * Create a provisioning request that does not get automatically approved (eg. ``num_vms``
            bigger than 1)
        * Wait for an e-mail to come, informing you that approval is pending
        * Depending on whether you want to do manual approval or edit approval, do:
            * MANUAL: manually approve the request in UI
            * EDIT: Edit the request in UI so it conforms the rules for auto-approval.
        * Wait for an e-mail with approval
        * Wait until the request finishes
        * Wait until an email with provisioning complete

    Metadata:
        test_flag: provision
        suite: infra_provisioning

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/8h
    """
    # generate_tests makes sure these have values
    # template, host, datastore = map(provisioning.get, ('template', 'host', 'datastore'))

    # It will provision two of them
    # All the subject checks are normalized, because of newlines and capitalization

    vm_names = [vm_name + "001", vm_name + "002"]
    if provider.one_of(CloudProvider):
        requester = ""
        vm_type = "instance"
    else:
        requester = "vm_provision@cfmeqe.com "  # include trailing space for clean formatting
        vm_type = "virtual machine"
    collection = appliance.provider_based_collection(provider)
    inst_args = {
        'catalog': {
            'vm_name': vm_name,
            'num_vms': '2'
        }
    }

    vm = collection.create(vm_name, provider, form_values=inst_args, wait=False)
    try:
        wait_for(
            lambda: len(smtp_test.get_emails()) >= 2,
            num_sec=90,
            delay=3
        )
    except TimedOutError:
        pytest.fail('Did not receive at least 2 emails from provisioning request, received: {}'
                    .format(smtp_test.get_emails()))

    pending_subject = normalize_text("your {} request is pending".format(vm_type))
    # requester includes the trailing space
    pending_from = normalize_text("{} request from {}pending approval".format(vm_type, requester))

    received_pending = [normalize_text(m["subject"]) for m in smtp_test.get_emails()]
    # Looking for each expected subject in the list of received subjects with partial match
    for subject in [pending_subject, pending_from]:
        soft_assert(any(subject in r_sub for r_sub in received_pending),
                    'Expected subject [{}], not matched in received subjects [{}]'
                    .format(subject, received_pending))

    smtp_test.clear_database()

    cells = {'Description': 'Provision from [{}] to [{}###]'.format(vm.template_name, vm.name)}
    provision_request = appliance.collections.requests.instantiate(cells=cells)
    if edit:
        # Automatic approval after editing the request to conform
        new_vm_name = '{}-xx'.format(vm_name)
        modifications = {
            'catalog': {
                'num_vms': "1",
                'vm_name': new_vm_name
            },
            'Description': 'Provision from [{}] to [{}]'.format(vm.template_name, new_vm_name)
        }
        provision_request.edit_request(values=modifications)
        vm_names = [new_vm_name]  # Will be just one now
        request.addfinalizer(
            lambda: collection.instantiate(new_vm_name, provider).cleanup_on_provider()
        )
    else:
        # Manual approval
        provision_request.approve_request(method='ui', reason="Approved")
        vm_names = [vm_name + "001", vm_name + "002"]  # There will be two VMs
        request.addfinalizer(
            lambda: [appliance.collections.infra_vms.instantiate(v_name,
                                                                 provider).cleanup_on_provider()
                     for v_name in vm_names]
        )

    try:
        wait_for(
            lambda: len(smtp_test.get_emails()) >= 2,
            num_sec=90,
            delay=3
        )
    except TimedOutError:
        pytest.fail('Did not receive at least 1 emails from provisioning request, received: {}'
                    .format(smtp_test.get_emails()))
    # requester includes the trailing space
    approved_subject = normalize_text("your {} request was approved".format(vm_type))
    approved_from = normalize_text("{} request from {}was approved".format(vm_type, requester))

    received_approved = [normalize_text(m["subject"]) for m in smtp_test.get_emails()]
    # Looking for each expected subject in the list of received subjects with partial match
    for subject in [approved_subject, approved_from]:
        soft_assert(any(subject in r_sub for r_sub in received_approved),
                    'Expected subject [{}], not matched in received subjects [{}]'
                    .format(subject, received_approved))

    smtp_test.clear_database()

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vms %s to appear on provider %s', ", ".join(vm_names), provider.key)
    wait_for(
        lambda: all(map(provider.mgmt.does_vm_exist, vm_names)),
        handle_exception=True,
        num_sec=600
    )

    provision_request.wait_for_request(method='ui')
    msg = "Provisioning failed with the message {}".format(provision_request.row.last_message.text)
    assert provision_request.is_succeeded(method='ui'), msg

    # account for multiple vms, specific names
    completed_subjects = [
        normalize_text("your {} request has completed vm name {}".format(vm_type, name))
        for name in vm_names
    ]
    expected_subject_count = len(vm_names)
    # Wait for e-mails to appear
    try:
        wait_for(
            lambda: len(smtp_test.get_emails()) >= expected_subject_count,
            message="provisioning request completed emails",
            delay=5
        )
    except TimedOutError:
        pytest.fail('Did not receive enough emails (> {}) from provisioning request, received: {}'
                    .format(expected_subject_count, smtp_test.get_emails()))

    received_complete = [normalize_text(m['subject']) for m in smtp_test.get_emails()]
    for expected_subject in completed_subjects:
        soft_assert(
            any(expected_subject in subject for subject in received_complete),
            'Expected subject [{}], not matched in received subjects [{}]'
            .format(subject, received_complete)
        )


@test_requirements.rest
@pytest.mark.parametrize('auto', [True, False], ids=["Auto", "Manual"])
@pytest.mark.meta(blockers=[
    BZ(1720751, unblock=lambda provider: not provider.one_of(SCVMMProvider))
])
def test_provision_from_template_using_rest(appliance, request, provider, vm_name, auto):
    """ Tests provisioning from a template using the REST API.

    Metadata:
        test_flag: provision, rest

    Polarion:
        assignee: pvala
        casecomponent: Provisioning
        caseimportance: high
        initialEstimate: 1/30h
    """
    if auto:
        form_values = {"vm_fields": {"placement_auto": True}}
    else:
        form_values = None
    collection = appliance.provider_based_collection(provider)
    instance = collection.create_rest(vm_name, provider, form_values=form_values)

    wait_for(
        lambda: instance.exists,
        num_sec=1000, delay=5, message="VM {} becomes visible".format(vm_name)
    )

    @request.addfinalizer
    def _cleanup():
        logger.info('Instance cleanup, deleting %s', instance.name)
        try:
            instance.cleanup_on_provider()
        except Exception as ex:
            logger.warning('Exception while deleting instance fixture, continuing: {}'
                           .format(ex.message))


@pytest.fixture(scope="module")
def original_request_class(appliance):
    return (appliance.collections.domains.instantiate(name='ManageIQ')
            .namespaces.instantiate(name='Cloud')
            .namespaces.instantiate(name='VM')
            .namespaces.instantiate(name='Provisioning')
            .namespaces.instantiate(name='StateMachines')
            .classes.instantiate(name='Methods'))


@pytest.fixture(scope="module")
def modified_request_class(request, domain, original_request_class):
    original_request_class.copy_to(domain)
    klass = (domain
             .namespaces.instantiate(name='Cloud')
             .namespaces.instantiate(name='VM')
             .namespaces.instantiate(name='Provisioning')
             .namespaces.instantiate(name='StateMachines')
             .classes.instantiate(name='Methods'))
    request.addfinalizer(klass.delete_if_exists)
    return klass


@pytest.fixture(scope="module")
def copy_domains(original_request_class, domain):
    methods = ['openstack_PreProvision', 'openstack_CustomizeRequest']
    for method in methods:
        original_request_class.methods.instantiate(name=method).copy_to(domain)


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[BZ(1713632)])
@pytest.mark.parametrize("disks", [1, 2])
@pytest.mark.provider([OpenStackProvider], required_fields=[['provisioning', 'image']],
                      override=True)
def test_cloud_provision_from_template_with_attached_disks(
        appliance, request, instance_args, provider, disks, soft_assert, domain,
        modified_request_class, copy_domains, provisioning):
    """ Tests provisioning from a template and attaching disks

    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    vm_name, inst_args = instance_args
    # Modify availiability_zone for Azure provider
    if provider.one_of(AzureProvider):
        recursive_update(inst_args, {'environment': {'availability_zone': provisioning("av_set")}})

    device_name = "vd{}"
    device_mapping = []

    volumes = provider.mgmt.volume_configurations(1, n=disks)

    @request.addfinalizer
    def delete_volumes():
        for volume in volumes:
            provider.mgmt.delete_volume(volume)

    # Set up automate
    for i, volume in enumerate(volumes, 0):
        # note the boot_index specifies an ordering in which the disks are tried to
        # boot from. The value -1 means "never".
        device_mapping.append(
            {'boot_index': 0 if i == 0 else -1,
            'uuid': volume,
            'device_name': device_name.format(chr(ord("a") + i))})

        if i == 0:
            provider.mgmt.capi.volumes.set_bootable(volume, True)

    method = modified_request_class.methods.instantiate(name="openstack_PreProvision")

    view = navigate_to(method, 'Details')
    former_method_script = view.script.get_value()

    disk_mapping = []
    for mapping in device_mapping:
        one_field = dedent("""{{
            :boot_index => {boot_index},
            :uuid => "{uuid}",
            :device_name => "{device_name}",
            :source_type => "volume",
            :destination_type => "volume",
            :volume_size => 1,
            :delete_on_termination => false
        }}""")
        disk_mapping.append(one_field.format(**mapping))

    volume_method = dedent("""
        clone_options = {{
        :image_ref => nil,
        :block_device_mapping_v2 => [
            {}
        ]
        }}

        prov = $evm.root["miq_provision"]
        prov.set_option(:clone_options, clone_options)
    """)
    with update(method):
        method.script = volume_method.format(",\n".join(disk_mapping))

    @request.addfinalizer
    def _finish_method():
        with update(method):
            method.script = former_method_script

    instance = appliance.collections.cloud_instances.create(vm_name,
                                                            provider,
                                                            form_values=inst_args)

    @request.addfinalizer
    def delete_vm_and_wait_for_gone():
        instance.cleanup_on_provider()
        wait_for(lambda: not instance.exists_on_provider, num_sec=180, delay=5)

    for volume_id in volumes:
        attachments = provider.mgmt.volume_attachments(volume_id)
        soft_assert(
            vm_name in attachments,
            'The vm {} not found among the attachemnts of volume {}:'.format(
                vm_name, volume_id, attachments))

    for device in device_mapping:
        provider_devpath = provider.mgmt.volume_attachments(device['uuid'])[vm_name]
        expected_devpath = '/dev/{}'.format(device['device_name'])
        soft_assert(
            provider_devpath == expected_devpath,
            'Device {} is not attached to expected path: {} but to: {}'.format(
                device['uuid'], expected_devpath, provider_devpath))


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[BZ(1746931)])
@pytest.mark.provider([OpenStackProvider], required_fields=[['provisioning', 'image']],
                      override=True)
def test_provision_with_boot_volume(request, instance_args, provider, soft_assert,
                                    modified_request_class, appliance, copy_domains):
    """ Tests provisioning from a template and attaching one booting volume.

    Metadata:
        test_flag: provision, volumes

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    vm_name, inst_args = instance_args

    image = inst_args.get('template_name')

    volume = provider.mgmt.create_volume(1, imageRef=provider.mgmt.get_template(image).uuid)
    request.addfinalizer(lambda: provider.mgmt.delete_volume(volume))

    # Set up automate
    method = modified_request_class.methods.instantiate(name="openstack_CustomizeRequest")
    view = navigate_to(method, 'Details')
    former_method_script = view.script.get_value()
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
            method.script = former_method_script

    instance = appliance.collections.cloud_instances.create(vm_name,
                                                            provider,
                                                            form_values=inst_args)

    @request.addfinalizer
    def delete_vm_and_wait_for_gone():
        instance.cleanup_on_provider()  # To make it possible to delete the volume
        wait_for(lambda: not instance.exists_on_provider, num_sec=180, delay=5)

    request_description = 'Provision from [{}] to [{}]'.format(image, instance.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')

    msg = "Provisioning failed with the message {}".format(
        provision_request.row.last_message.text)
    assert provision_request.is_succeeded(method='ui'), msg
    soft_assert(instance.name in provider.mgmt.volume_attachments(volume))
    soft_assert(provider.mgmt.volume_attachments(volume)[instance.name] == "/dev/vda")


# Not collected for EC2 in generate_tests above
@pytest.mark.meta(blockers=[BZ(1746931)])
@pytest.mark.provider([OpenStackProvider], required_fields=[['provisioning', 'image']],
                      override=True)
def test_provision_with_additional_volume(request, instance_args, provider, small_template,
                                          soft_assert, modified_request_class, appliance,
                                          copy_domains):
    """ Tests provisioning with setting specific image from AE and then also making it create and
    attach an additional 3G volume.

    Metadata:
        test_flag: provision, volumes

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    vm_name, inst_args = instance_args

    # Set up automate
    method = modified_request_class.methods.instantiate(name="openstack_CustomizeRequest")
    try:
        image_id = provider.mgmt.get_template(small_template.name).uuid
    except KeyError:
        pytest.skip("No small_template in provider data!")

    view = navigate_to(method, 'Details')
    former_method_script = view.script.get_value()
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

    @request.addfinalizer
    def _finish_method():
        with update(method):
            method.script = former_method_script

    def cleanup_and_wait_for_instance_gone():
        instance.mgmt.refresh()
        prov_instance_raw = instance.mgmt.raw
        instance_volumes = getattr(prov_instance_raw, 'os-extended-volumes:volumes_attached')

        instance.cleanup_on_provider()
        wait_for(lambda: not instance.exists_on_provider, num_sec=180, delay=5)

        # Delete the volumes.
        for volume in instance_volumes:
            provider.mgmt.delete_volume(volume['id'])

    instance = appliance.collections.cloud_instances.create(
        vm_name, provider, form_values=inst_args)
    request.addfinalizer(cleanup_and_wait_for_instance_gone)

    request_description = 'Provision from [{}] to [{}]'.format(small_template.name, instance.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    try:
        provision_request.wait_for_request(method='ui')
    except Exception as e:
        logger.info(
            "Provision failed {}: {}".format(e, provision_request.request_state))
        raise
    assert provision_request.is_succeeded(method='ui'), (
        "Provisioning failed with the message {}".format(
            provision_request.row.last_message.text))

    instance.mgmt.refresh()
    prov_instance_raw = instance.mgmt.raw

    assert hasattr(prov_instance_raw, 'os-extended-volumes:volumes_attached')
    volumes_attached = getattr(prov_instance_raw, 'os-extended-volumes:volumes_attached')
    assert len(volumes_attached) == 1
    volume_id = volumes_attached[0]["id"]
    assert provider.mgmt.volume_exists(volume_id)
    volume = provider.mgmt.get_volume(volume_id)
    assert volume.size == 3


@test_requirements.tag
def test_provision_with_tag(appliance, vm_name, tag, provider, request):
    """ Tests tagging instance using provisioning dialogs.

    Steps:
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, pick a tag.
        * Submit the provisioning request and wait for it to finish.
        * Visit instance page, it should display the selected tags
    Metadata:
        test_flag: provision

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/4h
    """
    inst_args = {'purpose': {
        'apply_tags': Check_tree.CheckNode(
            ['{} *'.format(tag.category.display_name), tag.display_name])}}
    collection = appliance.provider_based_collection(provider)
    instance = collection.create(vm_name, provider, form_values=inst_args)
    request.addfinalizer(instance.cleanup_on_provider)
    assert tag in instance.get_tags(), 'Provisioned instance does not have expected tag'


@pytest.mark.tier(2)
@test_requirements.multi_region
@test_requirements.provision
@pytest.mark.long_running
def test_provision_from_template_from_global_region(setup_multi_region_cluster,
                                                    multi_region_cluster,
                                                    activate_global_appliance,
                                                    setup_remote_provider,
                                                    provisioned_instance):
    """
    Polarion:
        assignee: izapolsk
        caseimportance: high
        casecomponent: Provisioning
        initialEstimate: 1/10h
    """
    assert provisioned_instance.exists_on_provider, "Instance wasn't provisioned successfully"
