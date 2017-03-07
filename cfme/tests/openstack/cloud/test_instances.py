"""Tests for Openstack cloud instances"""

import fauxfactory
import pytest
import random

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.web_ui import Quadicon
from utils import testgen
from utils.appliance.implementations.ui import navigate_to

pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.mark.usefixtures("setup_provider_modscope")
@pytest.fixture(scope='function')
def active_instance(provider):
    instances = provider.mgmt._get_all_instances()
    for inst in instances:
        if inst.status == 'ACTIVE':
            return OpenStackInstance(inst.name, provider)

    inst = random.choice(instances)
    inst = OpenStackInstance(inst.name, provider)
    inst.power_control_from_provider(OpenStackInstance.START)
    navigate_to(inst, 'Details')
    inst.wait_for_instance_state_change(OpenStackInstance.STATE_ON)
    return inst


@pytest.mark.usefixtures("setup_provider_modscope")
@pytest.fixture(scope='function')
def shelved_instance(provider):
    instances = provider.mgmt._get_all_instances()
    for inst in instances:
        if inst.status == 'SHELVED':
            return OpenStackInstance(inst.name, provider)

    inst = random.choice(instances)
    inst = OpenStackInstance(inst.name, provider)
    inst.power_control_from_provider(OpenStackInstance.SHELVE)
    navigate_to(inst, 'Details')
    inst.wait_for_instance_state_change(OpenStackInstance.STATE_SHELVED)
    return inst


def test_create_instance(provider, soft_assert):
    """Creates an instance and verifies it appears on UI"""
    prov_data = provider.get_yaml_data()['provisioning']
    instance = OpenStackInstance(fauxfactory.gen_alpha(), provider,
                                 template_name=prov_data['image']['name'])
    navigate_to(instance, 'Provision')
    instance.create(fauxfactory.gen_email(), fauxfactory.gen_alpha(),
                    fauxfactory.gen_alpha(), prov_data['cloud_network'],
                    prov_data['instance_type'], False,
                    security_groups='default',
                    availability_zone=prov_data['availability_zone'],
                    cloud_tenant=prov_data['tenant'])
    instance.wait_to_appear()
    power_state = instance.get_detail(properties=('Power Management',
                                                  'Power State'))
    assert power_state == OpenStackInstance.STATE_ON

    vm_tmplt = instance.get_detail(properties=('Relationships', 'VM Template'))
    soft_assert(vm_tmplt == prov_data['image']['name'])

    # Assert other relationships in a loop
    props = [('Availability Zone', 'availability_zone'),
             ('Cloud Tenants', 'tenant'),
             ('Flavor', 'instance_type'),
             ('Virtual Private Cloud', 'cloud_network')]

    for p in props:
        v = instance.get_detail(properties=('Relationships', p[0]))
        soft_assert(v == prov_data[p[1]])


def test_stop_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.STOP)
    active_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    state = active_instance.get_detail(properties=('Power Management',
                                                   'Power State'))
    assert state == OpenStackInstance.STATE_OFF


def test_suspend_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.SUSPEND)
    active_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_SUSPENDED)
    state = active_instance.get_detail(properties=('Power Management',
                                                   'Power State'))
    assert state == OpenStackInstance.STATE_SUSPENDED


def test_pause_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.PAUSE)
    active_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_PAUSED)
    state = active_instance.get_detail(properties=('Power Management',
                                                   'Power State'))
    assert state == OpenStackInstance.STATE_PAUSED


def test_shelve_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.SHELVE)
    active_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_SHELVED)
    state = active_instance.get_detail(properties=('Power Management',
                                                   'Power State'))
    assert state == OpenStackInstance.STATE_SHELVED_OFFLOAD


def test_shelve_offload_instance(shelved_instance):
    shelved_instance.power_control_from_cfme(from_details=True,
                                             option=OpenStackInstance.SHELVE_OFFLOAD)
    shelved_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_SHELVED_OFFLOAD)
    state = shelved_instance.get_detail(properties=('Power Management',
                                                    'Power State'))
    assert state == OpenStackInstance.STATE_SHELVED_OFFLOAD


def test_start_instance(shelved_instance):
    shelved_instance.power_control_from_cfme(from_details=True,
                                             option=OpenStackInstance.START)
    shelved_instance.wait_for_instance_state_change(OpenStackInstance.STATE_ON)
    state = shelved_instance.get_detail(properties=('Power Management',
                                                    'Power State'))
    assert state == OpenStackInstance.STATE_ON


def test_soft_reboot_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.SOFT_REBOOT)
    active_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_REBOOTING)

    state = active_instance.get_detail(properties=('Power Management',
                                                   'Power State'))
    assert state == OpenStackInstance.STATE_ON


def test_hard_reboot_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.HARD_REBOOT)
    active_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_REBOOTING)

    state = active_instance.get_detail(properties=('Power Management',
                                                   'Power State'))
    assert state == OpenStackInstance.STATE_ON


def test_delete_instance(active_instance):
    active_instance.power_control_from_cfme(from_details=True,
                                            option=OpenStackInstance.TERMINATE)
    active_instance.wait_for_instance_state_change(
        OpenStackInstance.STATE_UNKNOWN)

    assert active_instance.name not in active_instance.provider.mgmt.list_vm()
    navigate_to(active_instance, 'AllForProvider')
    assert active_instance.name not in Quadicon.all()
