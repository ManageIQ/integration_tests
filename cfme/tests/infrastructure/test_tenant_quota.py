# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.provisioning import do_vm_provisioning
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.generators import random_vm_name

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module")
]


@pytest.fixture
def vm_name():
    return random_vm_name()


@pytest.fixture
def template_name(provisioning):
    return provisioning["template"]


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
        item_type=provisioning['catalog_item_type'],
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
        [('cpu', 2), {'hardware': {'num_sockets': '8'}}, '', False],
        [('storage', 0.01), {}, '', False],
        [('memory', 2), {'hardware': {'memory': '4096'}}, '', False],
        [('vm', 1), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_lifecycle(appliance, provider, setup_provider,
                                            set_roottenant_quota, extra_msg, custom_prov_data,
                                            approve, prov_data, vm_name, template_name):
    """Test Tenant Quota in UI"""
    prov_data.update(custom_prov_data)
    prov_data['catalog']['vm_name'] = vm_name
    do_vm_provisioning(appliance, template_name=template_name, provider=provider, vm_name=vm_name,
                       provisioning_data=prov_data, smtp_test=False, wait=False, request=None)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}{}]'.format(template_name, vm_name, extra_msg)
    provision_request = appliance.collections.requests.instantiate(request_description)
    if approve:
        provision_request.approve_request(method='ui', reason="Approved")
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg'],
    [
        [('cpu', 2), {'hardware': {'num_sockets': '8'}}, ''],
        [('storage', 0.01), {}, ''],
        [('memory', 2), {'hardware': {'memory': '4096'}}, ''],
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
