"""Tests for Openstack cloud instances"""

import fauxfactory
import pytest

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from utils import testgen
from utils.appliance.implementations.ui import navigate_to

pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


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
    power_state = instance.get_detail('Power Management', 'Power State')
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
