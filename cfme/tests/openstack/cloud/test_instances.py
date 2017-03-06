"""Tests for Openstack cloud instances"""

import fauxfactory
import functools
import pytest

from cfme.cloud.instance.openstack import OpenStackInstance
from cfme.cloud.provider.openstack import OpenStackProvider
from utils import testgen
from utils.appliance.implementations.ui import navigate_to

pytest_generate_tests = testgen.generate([OpenStackProvider],
                                         scope='module')

pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


def test_create_instance(provider):
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
    assert instance.get_detail('Power Management', 'Power State') == 'on'

    # Assert displayed relationships
    get_relation = functools.partial(instance.get_detail, 'Relationships')
    assert get_relation('Availability Zone') == prov_data['availability_zone']
    assert get_relation('Cloud Tenants') == prov_data['tenant']
    assert get_relation('Flavor') == prov_data['instance_type']
    assert get_relation('VM Template') == prov_data['image']['name']
    assert get_relation('Virtual Private Cloud') == prov_data['cloud_network']
