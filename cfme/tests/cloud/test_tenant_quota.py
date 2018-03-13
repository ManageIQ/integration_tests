# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.instance import Instance
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI, ViaUI
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
def prov_data(vm_name, template_name):
    return {
        "catalog": {'vm_name': vm_name, 'catalog_name': {'name': template_name}},
        "environment": {'automatic_placement': True},
        'properties': {'instance_type': partial_match('m1.large')}
    }


@pytest.fixture
def custom_prov_data(request, prov_data, vm_name, template_name):
    value = request.param
    prov_data.update(value)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['catalog']['catalog_name'] = {'name': template_name}


@pytest.fixture
def set_roottenant_quota(request, roottenant, appliance):
    field, value = request.param
    roottenant.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alert are on requests page
    appliance.server.browser.refresh()
    roottenant.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture
def catalog_item(appliance, provider, provisioning, template_name, dialog, catalog, prov_data):
    collection = appliance.collections.catalog_items
    yield collection.create(appliance.collections.catalog_items.OPENSTACK,
                            name='test_{}'.format(fauxfactory.gen_alphanumeric()),
                            description='test catalog',
                            display_in=True,
                            catalog=catalog,
                            dialog=dialog,
                            prov_data=prov_data)


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
def test_tenant_quota_enforce_via_lifecycle_cloud(request, appliance, provider, setup_provider,
                                            set_roottenant_quota, extra_msg, custom_prov_data,
                                            approve, prov_data, vm_name, template_name):
    """Test Tenant Quota in UI"""
    prov_data.update(custom_prov_data)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data.update({
        'request': {'email': 'test_{}@example.com'.format(fauxfactory.gen_alphanumeric())}})
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
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'context'],
    [
        [('cpu', 2), {}, '', ViaUI],
        [('cpu', 2), {}, '', ViaSSUI],
        [('storage', 0.001), {}, '', ViaUI],
        [('storage', 0.001), {}, '', ViaSSUI],
        [('memory', 2), {}, '', ViaUI],
        [('memory', 2), {}, '', ViaSSUI],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', ViaUI],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', ViaSSUI]
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data'],
    ids=['max_cpu-ViaUI', 'max_cpu-ViaSSUI', 'max_storage-ViaUI', 'max_storage-ViaSSUI',
         'max_memory-ViaUI', 'max_memory-ViaSSUI', 'max_vms-ViaUI', 'max_vms-ViaSSUI']
)
def test_tenant_quota_enforce_via_service_cloud(request, appliance, provider, setup_provider,
                                                set_roottenant_quota, extra_msg, context,
                                                custom_prov_data, template_name, catalog_item):
    """Test Tenant Quota in UI and SSUI"""
    if context is ViaUI:
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                           catalog_item.name)
        service_catalogs.order()
    else:
        with appliance.context.use(context):
            service = ServiceCatalogs(appliance, name=catalog_item.name)
            service.add_to_shopping_cart()
            service.order()
    # nav to requests page to check quota validation
    request_description = 'Provisioning Service [{0}] from [{0}]'.format(catalog_item.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"

    @request.addfinalizer
    def delete():
        provision_request.remove_request()
        catalog_item.delete()
