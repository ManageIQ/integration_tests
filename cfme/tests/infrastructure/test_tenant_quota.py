import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module",
                         required_fields=[["provisioning", "template"]], selector=ONE_PER_TYPE)
]


@pytest.fixture
def set_default(provider, request):
    """This fixture is used to return paths for provisioning_entry_point, reconfigure_entry_point
       and retirement_entry_point. The value of 'provisioning_entry_point' is required while
       creating new catalog item in 'test_service_infra_tenant_quota_with_default_entry_point' test.
       But other tests does not require these values since those tests takes default values hence
       providing default value. So in this file, this fixture - 'set_default'
       must be used in all tests of quota which are related to services where catalog item needs to
       be created with specific values for these entries.
    """
    with_prov = (
        "Datastore", "ManageIQ (Locked)", "{}".format(provider.string_name), "VM", "Provisioning",
        "StateMachines", "ProvisionRequestApproval", "Default (Default)"
    )
    default = (
        "Service", "Provisioning", "StateMachines", "ServiceProvision_Template",
        "CatalogItemInitialization"
    )
    return with_prov if request.param else default


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


@pytest.fixture(scope='function')
def catalog_item(appliance, provider, dialog, catalog, prov_data, set_default):
    collection = appliance.collections.catalog_items
    catalog_item = collection.create(
        provider.catalog_item_type,
        name='test_{}'.format(fauxfactory.gen_alphanumeric()),
        description='test catalog',
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        prov_data=prov_data,
        provider=provider,
        provisioning_entry_point=set_default)
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


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
def test_tenant_quota_enforce_via_lifecycle_infra(appliance, provider, set_roottenant_quota,
                                                  extra_msg, custom_prov_data, approve, prov_data,
                                                  vm_name, template_name):
    """Test Tenant Quota in UI and SSUI

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        tags: quota
    """
    prov_data.update(custom_prov_data)
    prov_data['catalog']['vm_name'] = vm_name
    do_vm_provisioning(appliance, template_name=template_name, provider=provider, vm_name=vm_name,
                       provisioning_data=prov_data, wait=False, request=None)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{template}] to [{vm}{msg}]'.format(
        template=template_name, vm=vm_name, msg=extra_msg)
    provision_request = appliance.collections.requests.instantiate(request_description)
    if approve:
        provision_request.approve_request(method='ui', reason="Approved")
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.rhv3
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'set_default'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, '', False],
        [('storage', '0.01'), {}, '', False],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, '', False],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', False],
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data', 'set_default'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_service_infra(request, appliance, context, set_roottenant_quota,
                                                extra_msg, set_default, custom_prov_data,
                                                catalog_item):
    """Tests quota enforcement via service infra

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        tags: quota
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
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.rhv2
@pytest.mark.meta(automates=[1467644])
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
def test_tenant_quota_vm_reconfigure(request, appliance, set_roottenant_quota, small_vm,
                                     custom_prov_data):
    """Tests quota with vm reconfigure

    Bugzilla:
        1467644

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
        tags: quota
    """
    new_config = small_vm.configuration.copy()
    setattr(new_config.hw, custom_prov_data['change'], custom_prov_data['value'])
    small_vm.reconfigure(new_config)

    # Description of reconfigure request changes with new configuration
    if custom_prov_data['change'] == 'mem_size':
        request_description = (
            f'VM Reconfigure for: {small_vm.name} - Memory: {new_config.hw.mem_size} MB'
        )
    else:
        request_description = (
            f'VM Reconfigure for: {small_vm.name} - Processor Sockets: {new_config.hw.sockets}, '
            f'Processor Cores Per Socket: {new_config.hw.cores_per_socket}, Total Processors: '
            f'{new_config.hw.cores_per_socket * new_config.hw.sockets}'
        )

    # nav to requests page to check quota validation
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


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
def test_setting_child_quota_more_than_parent(appliance, tenants_setup, parent_quota, child_quota,
                                              flash_text):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Provisioning
        caseimportance: high
        initialEstimate: 1/12h
        tags: quota
    """
    test_parent, test_child = tenants_setup
    view = navigate_to(test_parent, 'ManageQuotas')
    view.form.fill({'{}_cb'.format(parent_quota[0]): True,
                    '{}_txt'.format(parent_quota[0]): parent_quota[1]})
    view.save_button.click()
    view = navigate_to(test_child, 'ManageQuotas')
    view.form.fill({'{}_cb'.format(child_quota[0]): True,
                    '{}_txt'.format(child_quota[0]): child_quota[1]})
    view.save_button.click()
    message = (
        "Error when saving tenant quota: Validation failed:"
        if appliance.version < "5.10"
        else "Error when saving tenant quota: Validation failed: TenantQuota:"
    )
    view.flash.assert_message(
        "{message} {flash_text} allocated "
        "quota is over allocated, parent tenant does not have enough quota".format(
            message=message, flash_text=flash_text
        )
    )


@pytest.mark.long_running
@pytest.mark.provider([VMwareProvider], scope="module",
                      required_fields=[['templates', 'small_template']], selector=ONE_PER_TYPE)
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data'],
    [
        [('cpu', '2'), {'change': 'cores_per_socket', 'value': '4'}]
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_cores']
)
def test_vm_migration_after_assigning_tenant_quota(appliance, small_vm, set_roottenant_quota,
                                                   custom_prov_data, provider):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/6h
        tags: quota
        testSteps:
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


# Args of parametrize is the list of navigation parameters to order catalog item.
# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'set_default'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, '', True],
        [('storage', '0.01'), {}, '', True],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, '', True],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', True],
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data', 'set_default'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_service_infra_tenant_quota_with_default_entry_point(request, appliance, context,
                                                             set_roottenant_quota, extra_msg,
                                                             set_default, custom_prov_data,
                                                             catalog_item):
    """Test Tenant Quota in UI and SSUI by selecting field entry points.
       Quota has to be checked if it is working with field entry points also.

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        tags: quota
        setup:
            1. Add infrastructure provider
            2. Set quota for root tenant - 'My Company'
            3. Navigate to services > catalogs
            4. Create catalog item with selecting following field entry points:
                a.provisioning_entry_point = /ManageIQ (Locked)/Infrastructure/VM/Provisioning
                /StateMachines/ProvisionRequestApproval/Default
                b.retirement_entry_point = /Service/Retirement/StateMachines/ServiceRetirement
                /Default
            5. Add other information required in catalog for provisioning VM
        testSteps:
            1. Order the catalog item via UI and SSUI individually
        expectedResults:
            1. Request of vm provisioning via service catalog should be denied with reason:
               "Quota Exceeded"
    """
    with appliance.context.use(context):
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        if context is ViaSSUI:
            service_catalogs.add_to_shopping_cart()
        service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = 'Provisioning Service [{name}] from [{name}]'.format(
        name=catalog_item.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.fixture
def configure_mail(domain):
    """This fixture copies email instance to custom domain"""
    approver = fauxfactory.gen_email()
    default_recipient = fauxfactory.gen_email()
    from_user = fauxfactory.gen_email()
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Configuration"
    ).classes.instantiate(name="Email").instances.instantiate(name="Default").copy_to(domain.name)
    instance = (
        domain.namespaces.instantiate(name="Configuration").classes.instantiate(name="Email")
    ).instances.instantiate(name="Default")
    with update(instance):
        instance.fields = {
            "approver": {"value": approver},
            "default_recipient": {"value": default_recipient},
            "from": {"value": from_user},
        }
    yield approver, default_recipient, from_user


@pytest.mark.meta(automates=[1579031, 1759123])
@pytest.mark.tier(1)
@pytest.mark.provider([RHEVMProvider], override=True, selector=ONE)
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg'],
    [
        [('memory', '2'), {'hardware': {'memory': '4096'}}, ''],
    ],
    indirect=['set_roottenant_quota'],
    ids=['max_memory']
)
def test_quota_exceed_mail_with_more_info_link(configure_mail, appliance, provider,
                                               set_roottenant_quota, custom_prov_data, prov_data,
                                               extra_msg, vm_name, template_name):
    """
    Bugzilla:
        1579031
        1759123

    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Infra
        tags: quota
        setup:
            1. Copy instance ManageIQ/Configuration/Email/Default to custom domain
            2. Enter values for fields: approver, default_recipient, from and signature
        testSteps:
            1. Provide valid mail address while provisioning Vm to exceed quota
        expectedResults:
            1. Quota exceed mail should be sent
    """
    approver, default_recipient, from_user = configure_mail
    mail_to = fauxfactory.gen_email()
    prov_data.update(custom_prov_data)
    prov_data['catalog']['vm_name'] = vm_name

    with LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[
            f'"to"=>"{default_recipient}", "from"=>"{from_user}".*.Virtual Machine Request from '
            f'{mail_to} was Denied."',
            f'"to"=>"{mail_to}", "from"=>"{from_user}".*.Your Virtual Machine Request was Approved,'
            f' pending Quota Validation.".*'],
    ).waiting(timeout=120):

        do_vm_provisioning(appliance, template_name=template_name, provider=provider,
                           vm_name=vm_name, provisioning_data=prov_data, wait=False, request=None,
                           email=mail_to)

        # nav to requests page to check quota validation
        request_description = f'Provision from [{template_name}] to [{vm_name}{extra_msg}]'
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        assert provision_request.row.reason.text == "Quota Exceeded"
