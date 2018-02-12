# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.provisioning import do_vm_provisioning
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.generators import random_vm_name

from widgetastic.utils import partial_match

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module")
]


@pytest.fixture
def vm_name():
    return random_vm_name(context='quota')


@pytest.fixture
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture(scope="module")
def roottenant(appliance):
    return appliance.collections.tenants.get_root_tenant()


@pytest.fixture
def prov_data(vm_name, provisioning):
    return {
        "catalog": {'vm_name': vm_name},
        "environment": {'automatic_placement': True},
        "network": {'vlan': partial_match(provisioning['vlan'])}
    }


@pytest.fixture
def set_roottenant_quota(request, roottenant, appliance):
    field, value = request.param
    roottenant.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.browser.refresh()
    roottenant.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture
def catalog_item(provider, template_name, dialog, catalog, prov_data):
    yield CatalogItem(
        item_type=provider.catalog_name,
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


@pytest.fixture(scope='module')
def small_vm(provider, small_template_modscope):
    vm = VM.factory(random_vm_name(context='reconfig'), provider, small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()
    yield vm
    vm.delete_from_provider()


@pytest.mark.rhv2
# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'approve'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, '', False],
        [('storage', '0.01'), {}, '', False],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, '', False],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', True]
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


@pytest.mark.rhv3
# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, ''],
        [('storage', '0.01'), {}, ''],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, ''],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###']
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


@pytest.mark.rhv2
# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data'],
    [
        [('cpu', '2'), {'change': 'cores_per_socket', 'value': '4'}],
        [('cpu', '2'), {'change': 'sockets', 'value': '4'}],
        [('memory', '2'), {'change': 'mem_size', 'value': '4096'}]
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_cores', 'max_sockets', 'max_memory']
)
def test_tenant_quota_vm_reconfigure(appliance, provider, setup_provider, set_roottenant_quota,
                                     small_vm, custom_prov_data):
    original_config = small_vm.configuration.copy()
    new_config = small_vm.configuration.copy()
    setattr(new_config.hw, custom_prov_data['change'], custom_prov_data['value'])
    small_vm.reconfigure(new_config)
    assert small_vm.configuration != original_config
