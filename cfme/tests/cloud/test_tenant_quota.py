# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
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
    # configuration tenants, not cloud tenants
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
    yield collection.create(provider.catalog_item_type,
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
    prov_data.update({'template_name': template_name})
    appliance.collections.cloud_instances.create(vm_name, provider, prov_data)

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
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg'],
    [
        [('cpu', 2), {}, ''],
        [('storage', 0.001), {}, ''],
        [('memory', 2), {}, ''],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###']
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_service_cloud(request, appliance, provider, setup_provider,
                                                context, set_roottenant_quota, custom_prov_data,
                                                extra_msg, template_name, catalog_item):
    """Test Tenant Quota in UI and SSUI"""
    with appliance.context.use(context):
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        if context is ViaSSUI:
            service_catalogs.add_to_shopping_cart()
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
