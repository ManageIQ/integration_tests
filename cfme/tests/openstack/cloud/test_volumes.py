"""Tests for Openstack cloud volumes"""
import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.wait import wait_for_decorator

pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider], scope='module')
]


VOLUME_SIZE = 1


@pytest.fixture(scope='function')
def volume(appliance, provider):
    collection = appliance.collections.volumes
    storage_manager = '{} Cinder Manager'.format(provider.name)
    volume = collection.create(name=fauxfactory.gen_alpha(start="vol_"),
                               storage_manager=storage_manager,
                               tenant=provider.data['provisioning']['cloud_tenant'],
                               size=VOLUME_SIZE,
                               provider=provider)
    yield volume

    try:
        if volume.exists:
            volume.delete(wait=False)
    except Exception:
        logger.warning('Exception during volume deletion - skipping..')


@pytest.mark.regression
@pytest.fixture(scope='function')
def volume_with_type(appliance, provider):
    vol_type = provider.mgmt.capi.volume_types.create(name=fauxfactory.gen_alpha(start="type_"))
    volume_type = appliance.collections.volume_types.instantiate(vol_type.name, provider)

    @wait_for_decorator(delay=10, timeout=300,
                        message="Waiting for volume type to appear")
    def volume_type_is_displayed():
        volume_type.refresh()
        return volume_type.exists

    collection = appliance.collections.volumes
    storage_manager = '{} Cinder Manager'.format(provider.name)
    volume = collection.create(name=fauxfactory.gen_alpha(start="vol_"),
                               storage_manager=storage_manager,
                               tenant=provider.data['provisioning']['cloud_tenant'],
                               volume_type=volume_type.name,
                               size=VOLUME_SIZE,
                               provider=provider)
    yield volume

    if volume.exists:
        volume.delete(wait=False)

    if volume_type.exists:
        provider.mgmt.capi.volume_types.delete(vol_type)


@pytest.fixture(scope='function')
def new_instance(provider):
    instance_name = fauxfactory.gen_alpha(15, start="test_vol_")
    collection = provider.appliance.provider_based_collection(provider)
    instance = collection.create_rest(instance_name, provider)
    yield instance

    instance.cleanup_on_provider()


@pytest.mark.regression
def test_create_volume(volume, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    assert volume.exists
    assert volume.size == '{} GB'.format(VOLUME_SIZE)
    assert volume.tenant == provider.data['provisioning']['cloud_tenant']


@pytest.mark.regression
def test_edit_volume(volume, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_name = fauxfactory.gen_alpha(15, start="edited_")
    with update(volume):
        volume.name = new_name
    view = navigate_to(appliance.collections.volumes, 'All')
    assert view.entities.get_entity(name=new_name, surf_pages=True)


@pytest.mark.regression
def test_delete_volume(volume):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    volume.delete()
    assert not volume.exists


@pytest.mark.rfe
def test_create_volume_with_type(volume_with_type, provider):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    assert volume_with_type.exists
    assert volume_with_type.size == '{} GB'.format(VOLUME_SIZE)
    assert volume_with_type.tenant == provider.data['provisioning']['cloud_tenant']


@pytest.mark.rfe
def test_edit_volume_with_type(volume_with_type, appliance):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_name = fauxfactory.gen_alpha(15, start="edited_")
    with update(volume_with_type):
        volume_with_type.name = new_name
    view = navigate_to(appliance.collections.volumes, 'All')
    assert view.entities.get_entity(name=new_name, surf_pages=True)


@pytest.mark.rfe
def test_delete_volume_with_type(volume_with_type):
    """
    Polarion:
        assignee: rhcf3_machine
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    volume_with_type.delete()
    assert not volume_with_type.exists


@pytest.mark.regression
def test_volume_attach_detach_instance(volume, new_instance, appliance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    # TODO: Test Reset and Cancel
    initial_instance_count = volume.instance_count
    volume.attach_instance(new_instance.name)
    view = appliance.browser.create_view(navigator.get_class(volume, 'Details').VIEW)
    view.flash.assert_success_message(
        'Attaching Cloud Volume "{name}" to {instance} finished'.format(
            name=volume.name, instance=new_instance.name))

    @wait_for_decorator(delay=10, timeout=300,
                        message="Waiting for volume to be attached to instance")
    def volume_attached_to_instance():
        new_instance.refresh_relationships()
        return volume.instance_count == initial_instance_count + 1

    volume.detach_instance(new_instance.name)
    view = appliance.browser.create_view(navigator.get_class(volume, 'Details').VIEW)
    view.flash.assert_success_message(
        'Detaching Cloud Volume "{name}" from {instance} finished'.format(
            name=volume.name, instance=new_instance.name))

    @wait_for_decorator(delay=10, timeout=300,
                        message="Waiting for volume to be detached from instance")
    def volume_detached_from_instance():
        new_instance.refresh_relationships()
        return volume.instance_count == initial_instance_count
