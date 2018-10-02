# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI, ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module", selector=ONE_PER_TYPE)
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


@pytest.fixture(scope='module')
def tenants_setup(appliance):
    tenants = appliance.collections.tenants
    my_company = tenants.get_root_tenant()
    test_parent = tenants.create(name='test_parent{}'.format(fauxfactory.gen_alphanumeric()),
                                 description='test_parent{}'.format(fauxfactory.gen_alphanumeric()),
                                 parent=my_company)
    test_child = tenants.create(name='test_child{}'.format(fauxfactory.gen_alphanumeric()),
                                description='test_child{}'.format(fauxfactory.gen_alphanumeric()),
                                parent=test_parent)
    yield test_parent, test_child
    test_child.delete()
    test_parent.delete()


@pytest.fixture
def prov_data(vm_name, provisioning):
    return {
        "catalog": {'vm_name': vm_name},
        "environment": {'automatic_placement': True},
        "network": {'vlan': partial_match(provisioning['vlan'])}
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
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.browser.refresh()
    roottenant.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture
def catalog_item(appliance, provider, dialog, catalog, prov_data):
    collection = appliance.collections.catalog_items
    yield collection.create(
        provider.catalog_item_type,
        name='test_{}'.format(fauxfactory.gen_alphanumeric()),
        description='test catalog',
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        prov_data=prov_data)


@pytest.fixture(scope='module')
def small_vm(provider, small_template_modscope):
    vm = provider.appliance.collections.infra_vms.instantiate(random_vm_name(context='reconfig'),
                                                              provider,
                                                              small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()
    yield vm
    vm.cleanup_on_provider()


@pytest.fixture()
def check_hosts(small_vm, provider):
    """Fixture to return host"""
    if len(provider.hosts.all()) != 1:
        view = navigate_to(small_vm, 'Details')
        vm_host = view.entities.summary('Relationships').get_text_of('Host')
        hosts = [vds.name for vds in provider.hosts.all() if vds.name not in vm_host]
        return hosts[0]
    else:
        pytest.skip("There is only one host in the provider")


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
def test_tenant_quota_enforce_via_lifecycle_infra(appliance, provider, setup_provider,
                                            set_roottenant_quota, extra_msg, custom_prov_data,
                                            approve, prov_data, vm_name, template_name):
    """Test Tenant Quota in UI and SSUI

    Metadata:
        test_flag: quota
    """
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
@pytest.mark.meta(blockers=[BZ(1633540, forced_streams=['5.10'],
    unblock=lambda provider: not provider.one_of(RHEVMProvider))])
# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, ''],
        [('storage', '0.01'), {}, ''],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, ''],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###'],
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_service_infra(request, appliance, provider, setup_provider,
                                                context, set_roottenant_quota, extra_msg,
                                                custom_prov_data, catalog_item):
    """Tests quota enforcement via service infra

    Metadata:
        test_flag: quota
    """
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


@pytest.mark.rhv2
@pytest.mark.meta(blockers=[BZ(1626232, forced_streams=['5.10'])])
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
    """Tests quota with vm reconfigure

    Metadata:
        test_flag: quota
    """
    original_config = small_vm.configuration.copy()
    new_config = small_vm.configuration.copy()
    setattr(new_config.hw, custom_prov_data['change'], custom_prov_data['value'])
    small_vm.reconfigure(new_config)
    assert small_vm.configuration != original_config


@pytest.mark.parametrize(
    ['parent_quota', 'child_quota', 'flash_text'],
    [
        [('cpu', '1'), ('cpu', '2'), 'Cpu'],
        [('memory', '1'), ('memory', '2'), 'Mem'],
        [('storage', '1'), ('storage', '2'), 'Storage'],
        [('vm', '1'), ('vm', '2'), 'Vms'],
        [('template', '1'), ('template', '2'), 'Templates']
    ],
    ids=['cpu', 'memory', 'storage', 'vm', 'template']
)
def test_setting_child_quota_more_than_parent(tenants_setup, parent_quota, child_quota,
                                              flash_text):
    test_parent, test_child = tenants_setup
    view = navigate_to(test_parent, 'ManageQuotas')
    view.form.fill({'{}_cb'.format(parent_quota[0]): True,
                    '{}_txt'.format(parent_quota[0]): parent_quota[1]})
    view.save_button.click()
    view = navigate_to(test_child, 'ManageQuotas')
    view.form.fill({'{}_cb'.format(child_quota[0]): True,
                    '{}_txt'.format(child_quota[0]): child_quota[1]})
    view.save_button.click()
    view.flash.assert_message('Error when saving tenant quota: Validation failed: {} allocated '
                              'quota is over allocated, parent tenant does not have enough quota'.
                              format(flash_text))


@pytest.mark.long_running
@pytest.mark.provider([VMwareProvider], override=True, scope="module",
                      required_fields=[['templates', 'small_template']], selector=ONE_PER_TYPE)
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data'],
    [
        [('cpu', '2'), {'change': 'cores_per_socket', 'value': '4'}]
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_cores']
)
def test_vm_migration_after_assigning_tenant_quota(appliance, setup_provider, small_vm,
                                                   set_roottenant_quota,
                                                   custom_prov_data, provider):
    """prerequisite: Provider should be added

    steps:

    1. Create VM
    2. Assign tenant quota
    3. Migrate VM
    4. Check whether migration is successfully done

    """

    migrate_to = check_hosts(small_vm, provider)
    small_vm.migrate_vm(fauxfactory.gen_email(), fauxfactory.gen_alpha(),
                        fauxfactory.gen_alpha(), host=migrate_to)
    request_description = small_vm.name
    cells = {'Description': request_description, 'Request Type': 'Migrate'}
    migrate_request = appliance.collections.requests.instantiate(request_description, cells=cells,
                                                                 partial_check=True)
    migrate_request.wait_for_request(method='ui')
    msg = "Request failed with the message {}".format(migrate_request.row.last_message.text)
    assert migrate_request.is_succeeded(method='ui'), msg
