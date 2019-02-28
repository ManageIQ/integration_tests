# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from wrapanapi import VmState

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.volume import VolumeAllView
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.storage,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider(
        [OpenStackProvider, EC2Provider],
        scope='module',
        required_fields=[['provisioning', 'cloud_tenant']]
    ),
]

STORAGE_SIZE = 1


@pytest.fixture(params=["from_manager", "from_volume"])
def from_manager(request):
    if request.param == "from_manager":
        return True
    else:
        return False


@pytest.fixture(scope='module')
def volume(appliance, provider):
    # create new volume
    volume = create_volume(appliance, provider, should_assert=False)
    yield volume

    try:
        if volume.exists:
            volume.delete(wait=True)
    except Exception as e:
        logger.warning("{name}:{msg} Volume deletion - skipping...".format(
            name=type(e).__name__,
            msg=str(e)))


@pytest.fixture(scope="function")
def instance_fixture(appliance, provider, small_template):
    instance = appliance.collections.cloud_instances.instantiate(random_vm_name('stor'),
                                                                 provider,
                                                                 small_template.name)
    if not instance.exists_on_provider:
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    elif instance.provider.one_of(EC2Provider) and instance.mgmt.state == VmState.DELETED:
        instance.mgmt.rename('test_terminated_{}'.format(fauxfactory.gen_alphanumeric(8)))
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
    yield instance
    instance.cleanup_on_provider()


def create_volume(appliance, provider, is_from_manager=False, az=None, cancel=False,
                  should_assert=False):
    volume_collection = appliance.collections.volumes
    manager = appliance.collections.block_managers.filter({"provider": provider}).all()[0]
    if provider.one_of(OpenStackProvider):
        volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                          storage_manager=manager,
                                          tenant=provider.data['provisioning']['cloud_tenant'],
                                          volume_size=STORAGE_SIZE,
                                          provider=provider,
                                          cancel=cancel,
                                          from_manager=is_from_manager)
    elif provider.one_of(EC2Provider):
        az = az if az else provider.region + 'a'
        volume = volume_collection.create(name=fauxfactory.gen_alpha(),
                                          storage_manager=manager,
                                          volume_type='General Purpose SSD (GP2)',
                                          volume_size=STORAGE_SIZE,
                                          provider=provider,
                                          az=az,
                                          from_manager=is_from_manager,
                                          cancel=cancel)
    if should_assert:
        assert volume.exists
    return volume


def test_storage_volume_create_cancelled_validation(appliance, provider, from_manager):
    """ Test Attach instance to storage volume cancelled

    prerequisites:
        * Storage provider

    Steps:
        * Navigate to storage add volume page
        * Click Cancel button
        * Assert flash message

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    volume_collection = appliance.collections.volumes
    create_volume(appliance, provider, from_manager, cancel=True)

    view = volume_collection.create_view(VolumeAllView)
    view.flash.assert_message('Add of new Cloud Volume was cancelled by the user')


@pytest.mark.tier(1)
def test_storage_volume_crud(appliance, provider, from_manager):
    """ Test storage volume crud

    prerequisites:
        * Storage provider

    Steps:
        * Crate new volume
        * Delete volume

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """
    # create volume
    volume = create_volume(appliance, provider, from_manager, should_assert=True)

    # update volume
    old_name = volume.name
    new_name = fauxfactory.gen_alpha()
    updates = {'volume_name': new_name, 'volume_size': STORAGE_SIZE + 1}

    if from_manager:
        storage_manager = appliance.collections.block_managers.filter(
            {"provider": provider}).all()[0]
    else:
        storage_manager = None
    volume = volume.update(updates, storage_manager)
    wait_for(lambda: volume.size == '{} GB'.format(updates.get('volume_size')), delay=15,
             timeout=900)

    updates = {'volume_name': old_name}
    volume = volume.update(updates, storage_manager)

    # delete volume
    volume.delete(wait=True, storage_manager=storage_manager)
    assert not volume.exists


@pytest.mark.tier(1)
def test_storage_volume_attach_detach(appliance, provider, instance_fixture, from_manager):
    volume = create_volume(appliance, provider, from_manager, az=instance_fixture.
                           vm_default_args["environment"]["availability_zone"], should_assert=True)
    if from_manager:
        storage_manager = appliance.collections.block_managers.filter(
            {"provider": provider}).all()[0]
    else:
        storage_manager = None
    # attach
    volume.attach_instance(name=instance_fixture.name, mountpoint='/dev/sdm',
                           storage_manager=storage_manager)
    wait_for(lambda: volume.status == 'in-use', delay=15, timeout=600)

    # detach
    volume.detach_instance(name=instance_fixture.name, storage_manager=storage_manager)
    wait_for(lambda: volume.status == 'available', delay=15, timeout=600)


def test_storage_volume_edit_tag(volume):
    """ Test add and remove tag to storage volume

    prerequisites:
        * Storage Volume

    Steps:
        * Add tag and check
        * Remove tag and check

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
    """

    # add tag with category Department and tag communication
    added_tag = volume.add_tag()
    tag_available = volume.get_tags()
    assert tag_available[0].display_name == added_tag.display_name
    assert tag_available[0].category.display_name == added_tag.category.display_name

    # remove assigned tag
    volume.remove_tag(added_tag)
    tag_available = volume.get_tags()
    assert not tag_available


def test_multiple_cloud_volumes_tag_edit(appliance, soft_assert):
    """Test tag can be added to multiple volumes at once

    Polarion:
        assignee: anikifor
        initialEstimate: 1/12h
        casecomponent: Configuration
    """
    all_volumes = appliance.collections.volumes.all()
    volumes = all_volumes[:3] if len(all_volumes) > 4 else all_volumes
    assigned_tag = appliance.collections.volumes.add_tag(volumes)
    for item in volumes:
        tag_available = item.get_tags()
        soft_assert(any(
            tag.category.display_name == assigned_tag.category.display_name and
            tag.display_name == assigned_tag.display_name for tag in tag_available), (
            'Tag is not assigned to volume {}'.format(item.name)))

    # remove tags to multiple items at once
    appliance.collections.volumes.remove_tag(volumes, assigned_tag)
    for item in volumes:
        soft_assert(not item.get_tags())
