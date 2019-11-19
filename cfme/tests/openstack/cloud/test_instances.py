"""Tests for Openstack cloud instances"""
import fauxfactory
import pytest
from selenium.common.exceptions import TimeoutException
from wait_for import TimedOutError
from widgetastic.utils import partial_match
from wrapanapi.entities import VmState

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for
from cfme.utils.wait import wait_for_decorator

pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider], scope='module', required_fields=[
        ['provisioning', 'cloud_tenant'],
        ['provisioning', 'cloud_network'],
        ['provisioning', 'instance_type']])
]


VOLUME_SIZE = 1


@pytest.fixture(scope='function')
def new_instance(provider):
    prov_data = provider.data['provisioning']
    prov_form_data = {
        'request': {'email': fauxfactory.gen_email(),
                    'first_name': fauxfactory.gen_alpha(),
                    'last_name': fauxfactory.gen_alpha()},
        'catalog': {'num_vms': '1',
                    'vm_name': random_vm_name("osp")},
        'environment': {'cloud_network': prov_data['cloud_network'],
                        'cloud_tenant': prov_data['cloud_tenant']},
        'properties': {'instance_type': partial_match(prov_data['instance_type'])},
    }

    instance_name = prov_form_data['catalog']['vm_name']

    try:
        instance = provider.appliance.collections.cloud_instances.create(
            instance_name,
            provider,
            prov_form_data, find_in_cfme=True
        )

    except KeyError:
        # some yaml value wasn't found
        pytest.skip('Unable to find an image map in provider "{}" provisioning data: {}'
                    .format(provider, prov_data))

    yield instance
    try:
        instance.cleanup_on_provider()
    except Exception:
        pass


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

    if volume.exists:
        volume.delete(wait=False)


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


@pytest.mark.regression
def test_create_instance(new_instance, soft_assert):
    """Creates an instance and verifies it appears on UI

    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    view = navigate_to(new_instance, 'Details')
    prov_data = new_instance.provider.data['provisioning']
    power_state = view.entities.summary('Power Management').get_text_of('Power State')
    assert power_state == OpenStackInstance.STATE_ON

    vm_tmplt = view.entities.summary('Relationships').get_text_of('VM Template')
    soft_assert(vm_tmplt == prov_data['image']['name'])

    # Assert other relationships in a loop
    props = [('Availability Zone', 'availability_zone'),
             ('Cloud Tenants', 'cloud_tenant'),
             ('Flavor', 'instance_type')]

    if current_version() >= '5.7':
        props.append(('Virtual Private Cloud', 'cloud_network'))

    for p in props:
        v = view.entities.summary('Relationships').get_text_of(p[0])
        soft_assert(v == prov_data[p[1]])


@pytest.mark.regression
def test_stop_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.STOP)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_OFF


@pytest.mark.regression
def test_suspend_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SUSPEND)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SUSPENDED)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_SUSPENDED


@pytest.mark.regression
def test_pause_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.PAUSE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_PAUSED)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_PAUSED


@pytest.mark.regression
def test_shelve_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SHELVE)
    try:
        new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SHELVED)
    except TimedOutError:
        logger.warning("Timeout when waiting for instance state: 'shelved'. Skipping")
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state in (OpenStackInstance.STATE_SHELVED_OFFLOAD,
                     OpenStackInstance.STATE_SHELVED)


@pytest.mark.regression
def test_shelve_offload_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SHELVE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SHELVED)
    try:
        new_instance.power_control_from_cfme(from_details=True,
                                             option=OpenStackInstance.SHELVE_OFFLOAD)
    except TimeoutException:
        logger.warning("Timeout when initiating power state 'Shelve Offload'. Skipping")

    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SHELVED_OFFLOAD)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_SHELVED_OFFLOAD


@pytest.mark.regression
def test_start_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.mgmt.ensure_state(VmState.STOPPED)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.START)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_ON)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_ON


@pytest.mark.regression
def test_soft_reboot_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SOFT_REBOOT)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_REBOOTING)

    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state in (OpenStackInstance.STATE_ON,
                     OpenStackInstance.STATE_REBOOTING)


@pytest.mark.regression
def test_hard_reboot_instance(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.HARD_REBOOT)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_REBOOTING)

    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state in (OpenStackInstance.STATE_ON,
                     OpenStackInstance.STATE_REBOOTING)


@pytest.mark.regression
def test_delete_instance(new_instance, provider):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.TERMINATE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_UNKNOWN)

    assert not new_instance.exists_on_provider
    view = navigate_to(
        new_instance.appliance.collections.cloud_instances.filter({'provider': provider}),
        'AllForProvider')
    try:
        view.entities.get_entity(name=new_instance.name, surf_pages=True)
        assert False, "entity still exists"
    except ItemNotFound:
        pass


@pytest.mark.regression
@pytest.mark.provider([OpenStackProvider],
                      required_fields=[['provisioning', 'image', 'os_distro']],
                      scope='module')
def test_instance_operating_system_linux(new_instance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    view = navigate_to(new_instance, 'Details')
    os = view.entities.summary('Properties').get_text_of("Operating System")
    prov_data_os = new_instance.provider.data['provisioning']['image']['os_distro']
    assert os == prov_data_os, 'OS type mismatch: expected {} and got {}'.format(prov_data_os, os)


@pytest.mark.regression
def test_instance_attach_volume(volume, new_instance, appliance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    initial_volume_count = new_instance.volume_count
    new_instance.attach_volume(volume.name)
    view = appliance.browser.create_view(navigator.get_class(new_instance, 'AttachVolume').VIEW)
    view.flash.assert_success_message(
        'Attaching Cloud Volume "{}" to {} finished'.format(volume.name, new_instance.name))

    wait_for(lambda: new_instance.volume_count > initial_volume_count,
             delay=20,
             timeout=300, message="Waiting for volume to be attached to instance",
             fail_func=new_instance.refresh_relationships)


@pytest.mark.rfe
def test_instance_attach_detach_volume_with_type(volume_with_type, new_instance, appliance):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    initial_volume_count = new_instance.volume_count
    new_instance.attach_volume(volume_with_type.name)
    view = appliance.browser.create_view(navigator.get_class(new_instance, 'Details').VIEW)
    view.flash.assert_success_message(
        'Attaching Cloud Volume "{}" to {} finished'
        .format(volume_with_type.name, new_instance.name)
    )

    @wait_for_decorator(delay=10, timeout=300,
                        message="Waiting for volume to be attached to instance")
    def volume_attached_to_instance():
        new_instance.refresh_relationships()
        return new_instance.volume_count > initial_volume_count

    new_instance.detach_volume(volume_with_type.name)
    view = appliance.browser.create_view(navigator.get_class(new_instance, 'Details').VIEW)
    view.flash.assert_success_message(
        'Detaching Cloud Volume "{}" from {} finished'
        .format(volume_with_type.name, new_instance.name)
    )

    @wait_for_decorator(delay=10, timeout=300,
                        message="Waiting for volume to be detached from instance")
    def volume_detached_from_instance():
        new_instance.refresh_relationships()
        return new_instance.volume_count == initial_volume_count
