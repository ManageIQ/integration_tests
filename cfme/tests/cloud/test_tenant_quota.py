# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.instance import Instance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.generators import random_vm_name

pytestmark = [
    test_requirements.quota,
    pytest.mark.provider([OpenStackProvider], required_fields=[['provisioning', 'image']],
                         scope="module")
]


@pytest.fixture
def vm_name():
    return random_vm_name(context='quota')


@pytest.fixture
def template_name(provisioning):
    return provisioning["image"]["name"]


@pytest.fixture(scope="module")
def roottenant(appliance):
    return appliance.collections.tenants.get_root_tenant()


@pytest.fixture
def prov_data(vm_name):
    return {
        "catalog": {'vm_name': vm_name},
        "environment": {'automatic_placement': True},
    }


@pytest.fixture
def set_roottenant_quota(request, roottenant):
    field, value = request.param
    roottenant.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    roottenant.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture
def catalog_item(provider, provisioning, template_name, dialog, catalog, prov_data):
    yield CatalogItem(
        item_type=provisioning['item_type'],
        name='test_{}'.format(fauxfactory.gen_alphanumeric()),
        description="test catalog",
        display_in=True,
        provider=provider,
        catalog=catalog,
        catalog_name=template_name,
        dialog=dialog,
        prov_data=prov_data,
        vm_name=prov_data['catalog']['vm_name']
    )


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'approve'],
    [
        [('cpu', 2), {}, '', False],
        [('storage', 0.001), {}, '', False],
        [('memory', 2), {}, '', False],
        [('vm', 1), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_lifecycle(request, appliance, provider, setup_provider,
                                            set_roottenant_quota, extra_msg, custom_prov_data,
                                            approve, prov_data, vm_name, template_name):
    """Test Tenant Quota in UI"""
    prov_data.update(custom_prov_data)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data.update({
        'request': {'email': 'test_{}@example.com'.format(fauxfactory.gen_alphanumeric())},
        'properties': {'instance_type': partial_match('m1.large')}})
    instance = Instance.factory(vm_name, provider, template_name)
    instance.create(**prov_data)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}{}]'.format(template_name, vm_name, extra_msg)
    provision_request = appliance.collections.requests.instantiate(request_description)
    if approve:
        provision_request.approve_request(method='ui', reason="Approved")
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"

    request.addfinalizer(provision_request.remove_request)


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg'],
    [
        [('cpu', 2), {}, ''],
        [('storage', 0.001), {}, ''],
        [('memory', 2), {}, ''],
        [('vm', 1), {'catalog': {'num_vms': '4'}}, '###']
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_service(request, appliance, provider, setup_provider,
                                          set_roottenant_quota, extra_msg, custom_prov_data,
                                          prov_data, template_name, catalog_item):
    """Test Tenant Quota in UI"""
    catalog_item.provisioning_data.update(custom_prov_data)
    catalog_item.provisioning_data['catalog']['vm_name'] = catalog_item.vm_name
    catalog_item.provisioning_data.update({'properties': {
        'instance_type': partial_match('m1.large')}})
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name)
    service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = 'Provisioning Service [{0}] from [{0}]'.format(catalog_item.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"

    @request.addfinalizer
    def delete():
        provision_request.remove_request()
        catalog_item.delete()
