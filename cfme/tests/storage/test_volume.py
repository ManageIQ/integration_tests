# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.storage.volume import StorageManagerVolumeAllView
from cfme.storage.volume import VolumeAllView
from cfme.storage.volume import VolumeDetailsView
from cfme.utils.blockers import BZ
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
    name = fauxfactory.gen_alpha()
    if provider.one_of(OpenStackProvider):
        if appliance.version < "5.11":
            volume = volume_collection.create(name=name,
                                              tenant=provider.data['provisioning']['cloud_tenant'],
                                              volume_size=STORAGE_SIZE,
                                              provider=provider,
                                              cancel=cancel,
                                              from_manager=is_from_manager)
        else:
            volume = volume_collection.create(name=name,
                                              tenant=provider.data['provisioning']['cloud_tenant'],
                                              volume_size=STORAGE_SIZE,
                                              provider=provider,
                                              az=provider.data['provisioning']['availability_zone'],
                                              cancel=cancel,
                                              from_manager=is_from_manager)
    elif provider.one_of(EC2Provider):
        az = az if az else "{}a".format(provider.region)
        volume = volume_collection.create(name=name,
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

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        testSteps:
            1. Navigate to storage add volume page
            2. Click Cancel button
            3. Assert flash message
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

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        caseimportance: high
        testSteps:
            1. Create new volume
            2. Update volume
            3. Delete volume
    """
    # create volume
    volume = create_volume(appliance, provider, from_manager, should_assert=True)

    # update volume
    old_name = volume.name
    new_name = fauxfactory.gen_alpha()
    if provider.one_of(OpenStackProvider):
        updates = {'volume_name': new_name}
    else:
        updates = {'volume_name': new_name, 'volume_size': STORAGE_SIZE + 1}

    volume = volume.update(updates, from_manager)
    if provider.one_of(EC2Provider):
        wait_for(lambda: volume.size == '{} GB'.format(updates.get('volume_size')), delay=15,
                 timeout=900)

    updates = {'volume_name': old_name}
    volume = volume.update(updates, from_manager)

    # delete volume
    volume.delete(wait=True, from_manager=from_manager)
    assert not volume.exists


@pytest.mark.meta(blockers=[BZ(1684939, forced_streams=["5.10"],
                               unblock=lambda provider: provider.one_of(EC2Provider))])
@pytest.mark.tier(1)
def test_storage_volume_attach_detach(appliance, provider, instance_fixture, from_manager):
    """ Test storage volume attach/detach
    prerequisites:
        * Storage provider
        * Instance

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/4h
        casecomponent: Cloud
        startsin: 5.7
        caseimportance: high
        testSteps:
            1. Create new volume
            2. Attach that volume to instance
            3. Detach that volume from instance
            4. Delete that volume

    """
    volume = create_volume(appliance, provider, from_manager, az=instance_fixture.
                           vm_default_args["environment"]["availability_zone"], should_assert=True)

    # attach
    volume.attach_instance(name=instance_fixture.name, mountpoint='/dev/sdm',
                           from_manager=from_manager)
    wait_for(lambda: volume.status == 'in-use', delay=15, timeout=600)

    # detach
    volume.detach_instance(name=instance_fixture.name, from_manager=from_manager)
    wait_for(lambda: volume.status == 'available', delay=15, timeout=600)

    # cleanup
    volume.delete()


@pytest.mark.meta(blockers=[BZ(1684939, forced_streams=["5.10"],
                               unblock=lambda provider: provider.one_of(EC2Provider))])
@test_requirements.storage
def test_storage_volume_attached_delete(appliance, provider, instance_fixture, from_manager):
    """
    Requires:
        RHCF3-21779 - test_storage_volume_attach[openstack]

    Polarion:
        assignee: mmojzis
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.7
        testSteps:
            1. Check after attached status of volume in-used or not
            2. Now try to delete volume from Detail page
            3. Navigate on All page
            4. try to delete volume from All page
        expectedResults:
            1. check for flash message " Cloud Volume "Volume_name" cannot be
            removed because it is attached to one or more Instances "
            2.
            3.
            4. check for flash message " Cloud Volume "Volume_name" cannot be
            removed because it is attached to one or more Instances "
        """
    volume = create_volume(appliance, provider, from_manager, az=instance_fixture.
                           vm_default_args["environment"]["availability_zone"], should_assert=True)

    # attach
    volume.attach_instance(name=instance_fixture.name, mountpoint='/dev/sdm',
                           from_manager=from_manager)
    wait_for(lambda: volume.status == 'in-use', delay=15, timeout=600)

    try:
        volume.delete(from_manager=from_manager)
        pytest.fail("Attached volume was deleted!")
    except Exception:
        if from_manager:
            view = volume.browser.create_view(StorageManagerVolumeAllView,
                                              additional_context={'object': volume.parent.manager})
        else:
            view = volume.create_view(VolumeDetailsView)
        assert view.flash.assert_message('Cloud Volume "{}" cannot be removed because it is '
                                         'attached to one or more Instances'.format(volume.name))
    # detach
    volume.detach_instance(name=instance_fixture.name, from_manager=from_manager)
    wait_for(lambda: volume.status == 'available', delay=15, timeout=600)

    volume.delete()


@test_requirements.tag
def test_storage_volume_edit_tag(volume):
    """ Test add and remove tag to storage volume
    prerequisites:
        * Storage Volume

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Cloud
        testSteps:
            1. Add tag
            2. Remove tag
        expectedResults:
            1. Check that tag is added
            2. Checked that tag is removed
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


@test_requirements.tag
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
