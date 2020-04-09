import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.generators import random_vm_name

pytestmark = [
    test_requirements.quota,
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.provider([OpenStackProvider], required_fields=[['provisioning', 'image']],
                         scope="module")]


@pytest.fixture
def set_default(provider, request):
    """This fixture is used to return paths for provisioning_entry_point, reconfigure_entry_point
       and retirement_entry_point. The value of 'provisioning_entry_point' is required while
       creating new catalog item in 'test_service_cloud_tenant_quota_with_default_entry_point' test.
       But other tests does not require these values since those tests takes default values hence
       providing default value. So in this file, this fixture - 'set_default'
       must be used in all tests of quota which are related to services where catalog item needs to
       be created with specific values for these entries.
    """
    with_prov = (
        "Datastore", "ManageIQ (Locked)", f"{provider.string_name}", "VM", "Provisioning",
        "StateMachines", "ProvisionRequestApproval", "Default"
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
    return provisioning["image"]["name"]


@pytest.fixture
def prov_data(vm_name, template_name, provisioning):
    return {
        "catalog": {"vm_name": vm_name, "catalog_name": {"name": template_name}},
        "environment": {"automatic_placement": True},
        "properties": {
            "instance_type": partial_match(
                provisioning.get("instance_type2", "Instance type is not available")
            )
        },
    }


@pytest.fixture
def custom_prov_data(request, prov_data, vm_name, template_name):
    value = request.param
    prov_data.update(value)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['catalog']['catalog_name'] = {'name': template_name}


@pytest.fixture
def set_roottenant_quota(request, appliance):
    roottenant = appliance.collections.tenants.get_root_tenant()
    field, value = request.param
    roottenant.set_quota(**{f'{field}_cb': True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alert are on requests page
    appliance.server.browser.refresh()
    roottenant.set_quota(**{f'{field}_cb': False})


@pytest.fixture
def catalog_item(appliance, provider, provisioning, template_name, dialog, catalog, prov_data,
                 set_default):
    catalog_item = appliance.collections.catalog_items.create(
        provider.catalog_item_type,
        name=fauxfactory.gen_alphanumeric(start="test_"),
        description=fauxfactory.gen_alphanumeric(start="desc_"),
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        prov_data=prov_data,
        provisioning_entry_point=set_default,
    )
    yield catalog_item
    catalog_item.delete_if_exists()


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
def test_tenant_quota_enforce_via_lifecycle_cloud(request, appliance, provider,
                                                  set_roottenant_quota, extra_msg, custom_prov_data,
                                                  approve, prov_data, vm_name, template_name):
    """Test Tenant Quota in UI

    Polarion:
        assignee: tpapaioa
        casecomponent: Cloud
        initialEstimate: 1/10h
        tags: quota
    """
    prov_data.update(custom_prov_data)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data.update({
        'request': {'email': fauxfactory.gen_email()}})
    prov_data.update({'template_name': template_name})
    request_description = f'Provision from [{template_name}] to [{vm_name}{extra_msg}]'
    appliance.collections.cloud_instances.create(vm_name, provider, prov_data, auto_approve=approve,
                                                 override=True,
                                                 request_description=request_description)

    # nav to requests page to check quota validation
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'set_default'],
    [
        [('cpu', 2), {}, '', False],
        [('storage', 0.001), {}, '', False],
        [('memory', 2), {}, '', False],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', False]
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data', 'set_default'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_tenant_quota_enforce_via_service_cloud(request, appliance, context, set_roottenant_quota,
                                                set_default, custom_prov_data, extra_msg,
                                                template_name, catalog_item):
    """Test Tenant Quota in UI and SSUI

    Polarion:
        assignee: tpapaioa
        casecomponent: Cloud
        initialEstimate: 1/10h
        tags: quota
    """
    with appliance.context.use(context):
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        if context is ViaSSUI:
            service_catalogs.add_to_shopping_cart()
        service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = f'Provisioning Service [{catalog_item.name}] from [{catalog_item.name}]'
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


# Args of parametrize is the list of navigation parameters to order catalog item.
# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated,
# sequence is important here.
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_roottenant_quota', 'custom_prov_data', 'extra_msg', 'set_default'],
    [
        [('cpu', 2), {}, '', True],
        [('storage', 0.001), {}, '', True],
        [('memory', 2), {}, '', True],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_roottenant_quota', 'custom_prov_data', 'set_default'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_service_cloud_tenant_quota_with_default_entry_point(request, appliance, context,
                                                             set_roottenant_quota, set_default,
                                                             custom_prov_data, extra_msg,
                                                             catalog_item):
    """Test Tenant Quota in UI and SSUI by selecting field entry points.
       Quota has to be checked if it is working with field entry points also.

    Polarion:
        assignee: tpapaioa
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/12h
        tags: quota
        testSteps:
            1. Add cloud provider
            2. Set quota for root tenant - 'My Company'
            3. Navigate to services > catalogs
            4. Create catalog item with selecting following field entry points:
                a.provisioning_entry_point = /ManageIQ (Locked)/Cloud/VM/Provisioning
                /StateMachines/ProvisionRequestApproval/Default
                b.retirement_entry_point = /Service/Retirement/StateMachines/ServiceRetirement
                /Default
            5. Add other information required in catalog for provisioning VM
            6. Order the catalog item via UI and SSUI individually
    """
    with appliance.context.use(context):
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        if context is ViaSSUI:
            service_catalogs.add_to_shopping_cart()
        service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = f"Provisioning Service [{catalog_item.name}] from [{catalog_item.name}]"
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.fixture(scope="function")
def instance(appliance, provider, small_template, setup_provider):
    """Fixture to provision instance on the provider"""
    instance = appliance.collections.cloud_instances.instantiate(random_vm_name('pwr-c'),
                                                                 provider,
                                                                 small_template.name)
    if not instance.exists_on_provider:
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)

    yield instance
    instance.cleanup_on_provider()


@pytest.mark.tier(2)
@pytest.mark.parametrize(
    ("set_roottenant_quota"),
    [("storage", 0.001)],
    indirect=["set_roottenant_quota"],
    ids=["max_storage"],
)
def test_instance_quota_reconfigure_with_flavors(request, instance, set_roottenant_quota):
    """
    Note: Test reconfiguration of instance using flavors after setting quota but this is RFE which
    is not yet implemented. Hence this test cases is based on existing scenario. Where instance
    reconfiguration does honour quota. Also one more RFE(1506471) - 'Instance reconfiguration with
    flavors should work with request' is closed as WONTFIX. So this scenario is not considered in
    this test case.

    # TODO(ghubale@redhat.com): Update scenario of this test cases if RFE(1473325) got fixed for any
    # future version of cfme

    Bugzilla:
        1473325
        1506471

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/6h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: Cloud
        tags: quota
        testSteps:
            1. Add openstack provider
            2. Provision instance
            3. Set quota limit
            4. Reconfigure this instance with changing flavors
        expectedResults:
            1.
            2. Provision instance successfully
            3.
            4. Reconfiguring instance request should succeed
    """
    current_instance_type = instance.appliance.rest_api.collections.flavors.get(
        id=instance.rest_api_entity.flavor_id
    ).name
    flavor_name = (
        "m1.small (1 CPU, 2.0 GB RAM, 20.0 GB Root Disk)"
        if current_instance_type != "m1.small"
        else "m1.tiny (1 CPU, 0.5 GB RAM, 1.0 GB Root Disk)"
    )
    instance.reconfigure(flavor_name)
    provision_request = instance.appliance.collections.requests.instantiate(
        f"VM Cloud Reconfigure for: {instance.name} - Flavor: {flavor_name.split(' ')[0]}"
    )
    provision_request.wait_for_request(method="ui")
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.is_succeeded(method="ui"), "Instance reconfigure failed: {}".format(
        provision_request.row.last_message.text
    )
