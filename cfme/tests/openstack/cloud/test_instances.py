"""Tests for Openstack cloud instances"""

import fauxfactory
import pytest

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.infrastructure.host import Host
from cfme.web_ui import Quadicon
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.providers import get_crud
from utils.version import current_version

pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


@pytest.fixture(scope='function')
def new_instance(provider):
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
    return instance


def test_create_instance(new_instance, soft_assert):
    """Creates an instance and verifies it appears on UI"""
    navigate_to(new_instance, 'Details')
    prov_data = new_instance.provider.get_yaml_data()['provisioning']
    power_state = new_instance.get_detail(properties=('Power Management',
                                                      'Power State'))
    assert power_state == OpenStackInstance.STATE_ON

    vm_tmplt = new_instance.get_detail(properties=('Relationships',
                                                   'VM Template'))
    soft_assert(vm_tmplt == prov_data['image']['name'])

    # Assert other relationships in a loop
    props = [('Availability Zone', 'availability_zone'),
             ('Cloud Tenants', 'tenant'),
             ('Flavor', 'instance_type')]

    if current_version() >= '5.7':
        props.append(('Virtual Private Cloud', 'cloud_network'))

    for p in props:
        v = new_instance.get_detail(properties=('Relationships', p[0]))
        soft_assert(v == prov_data[p[1]])


def test_stop_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.STOP)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    state = new_instance.get_detail(properties=('Power Management',
                                                'Power State'))
    assert state == OpenStackInstance.STATE_OFF


def test_suspend_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SUSPEND)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SUSPENDED)
    state = new_instance.get_detail(properties=('Power Management', 'Power State'))
    assert state == OpenStackInstance.STATE_SUSPENDED


def test_pause_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.PAUSE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_PAUSED)
    state = new_instance.get_detail(properties=('Power Management',
                                                'Power State'))
    assert state == OpenStackInstance.STATE_PAUSED


def test_shelve_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SHELVE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SHELVED)
    state = new_instance.get_detail(properties=('Power Management',
                                                'Power State'))
    assert state in (OpenStackInstance.STATE_SHELVED_OFFLOAD,
                     OpenStackInstance.STATE_SHELVED)


def test_shelve_offload_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SHELVE)
    new_instance.power_control_from_cfme(option=OpenStackInstance.SHELVE_OFFLOAD)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_SHELVED_OFFLOAD)
    state = new_instance.get_detail(properties=('Power Management',
                                                'Power State'))
    assert state == OpenStackInstance.STATE_SHELVED_OFFLOAD


def test_start_instance(new_instance):
    new_instance.power_control_from_provider(OpenStackInstance.STOP)
    navigate_to(new_instance, 'Details')
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_OFF)
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.START)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_ON)
    state = new_instance.get_detail(properties=('Power Management',
                                                'Power State'))
    assert state == OpenStackInstance.STATE_ON


def test_soft_reboot_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.SOFT_REBOOT)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_REBOOTING)

    state = new_instance.get_detail(properties=('Power Management', 'Power State'))
    assert state in (OpenStackInstance.STATE_ON,
                     OpenStackInstance.STATE_REBOOTING)


def test_hard_reboot_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.HARD_REBOOT)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_REBOOTING)

    state = new_instance.get_detail(properties=('Power Management',
                                                'Power State'))
    assert state in (OpenStackInstance.STATE_ON,
                     OpenStackInstance.STATE_REBOOTING)


def test_delete_instance(new_instance):
    new_instance.power_control_from_cfme(from_details=True,
                                         option=OpenStackInstance.TERMINATE)
    new_instance.wait_for_instance_state_change(OpenStackInstance.STATE_UNKNOWN)

    assert new_instance.name not in new_instance.provider.mgmt.list_vm()
    navigate_to(new_instance, 'AllForProvider')
    assert new_instance.name not in [q.name for q in Quadicon.all()]


def test_list_vms_infra_node(provider, soft_assert):
    infra_provider = get_crud(provider.get_yaml_data()['infra_provider'])
    navigate_to(infra_provider, 'ProviderNodes')
    # Match hypervisors by IP with count of running VMs
    hvisors = dict()
    for hv in provider.mgmt.api.hypervisors.list():
        hvisors.update({hv.host_ip: hv.running_vms})

    # Skip non-compute nodes
    quads = filter(lambda q: 'Compute' in q.name, Quadicon.all())
    quads = [q.name for q in quads]
    for quad in quads:
        host = Host(quad, provider=infra_provider)
        navigate_to(host, 'Details')
        host_ip = host.get_detail('Properties', 'IP Address')
        vms = int(host.get_detail('Relationships', 'VMs'))
        soft_assert(hvisors[host_ip] == vms)
