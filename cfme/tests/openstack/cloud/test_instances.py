"""Tests for Openstack cloud instances"""

import fauxfactory
import pytest
from selenium.common.exceptions import TimeoutException
from wait_for import TimedOutError

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import ItemNotFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.version import current_version


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenStackProvider], scope='module')
]


@pytest.fixture(scope='function')
def new_instance(provider):
    prov_data = provider.data['provisioning']
    try:
        instance = provider.appliance.collections.cloud_instances.instantiate(
            fauxfactory.gen_alpha(),
            provider,
            template_name=prov_data['image']['name']
        )
        prov_form_data = {
            'request': {'email': fauxfactory.gen_email(),
                        'first_name': fauxfactory.gen_alpha(),
                        'last_name': fauxfactory.gen_alpha()},
            'catalog': {'num_vms': '1',
                        'vm_name': instance.name},
            'environment': {'cloud_network': prov_data['cloud_network']},
            'properties': {'instance_type': prov_data['instance_type']},
        }
    except KeyError:
        # some yaml value wasn't found
        pytest.skip('Unable to find an image map in provider "{}" provisioning data: {}'
                    .format(provider, prov_data))

    instance.create(**prov_form_data)
    instance.wait_to_appear()
    yield instance
    try:
        instance.power_control_from_provider(instance.TERMINATE)
    except:
        pass


def test_create_instance(new_instance, soft_assert):
    """Creates an instance and verifies it appears on UI"""
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


def test_stop_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.STOP)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_OFF


def test_suspend_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SUSPEND)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SUSPENDED)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_SUSPENDED


def test_pause_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.PAUSE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_PAUSED)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_PAUSED


def test_shelve_instance(new_instance):
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


def test_shelve_offload_instance(new_instance):
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


def test_start_instance(new_instance):
    new_instance.power_control_from_provider(OpenStackInstance.STOP)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.START)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_ON)
    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state == OpenStackInstance.STATE_ON


def test_soft_reboot_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SOFT_REBOOT)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_REBOOTING)

    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state in (OpenStackInstance.STATE_ON,
                     OpenStackInstance.STATE_REBOOTING)


def test_hard_reboot_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.HARD_REBOOT)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_REBOOTING)

    view = navigate_to(new_instance, 'Details')
    state = view.entities.summary('Power Management').get_text_of('Power State')
    assert state in (OpenStackInstance.STATE_ON,
                     OpenStackInstance.STATE_REBOOTING)


def test_delete_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.TERMINATE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_UNKNOWN)

    assert new_instance.name not in new_instance.provider.mgmt.list_vm()
    view = navigate_to(new_instance.parent, 'AllForProvider')
    try:
        view.entities.get_entity(name=new_instance.name, surf_pages=True)
        assert False, "entity still exists"
    except ItemNotFound:
        pass
