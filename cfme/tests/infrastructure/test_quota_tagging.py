import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update


pytestmark = [
    test_requirements.quota,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([RHEVMProvider, VMwareProvider], scope="module", selector=ONE_PER_TYPE)
]


@pytest.fixture(scope='module')
def admin_email(appliance):
    """Required for user quota tagging services to work, as it's mandatory for it's functioning."""
    user = appliance.collections.users
    admin = user.instantiate(name='Administrator')
    with update(admin):
        admin.email = fauxfactory.gen_email()
    yield
    with update(admin):
        admin.email = ''


@pytest.fixture
def vm_name():
    return random_vm_name(context='quota')


@pytest.fixture
def template_name(provider):
    if provider.one_of(RHEVMProvider):
        return provider.data.templates.get('full_template')['name']
    elif provider.one_of(VMwareProvider):
        return provider.data.templates.get('big_template')['name']


@pytest.fixture
def prov_data(provider, vm_name, template_name):
    if provider.one_of(RHEVMProvider):
        return {
            "catalog": {'vm_name': vm_name, 'catalog_name': {'name': template_name}},
            "environment": {'automatic_placement': True},
            "network": {'vlan': partial_match('ovirtmgmt')},
        }
    else:
        return {
            "catalog": {'vm_name': vm_name, 'catalog_name': {'name': template_name}},
            "environment": {'automatic_placement': True},
        }


@pytest.fixture(scope='module')
def domain(appliance):
    domain = appliance.collections.domains.create(
        fauxfactory.gen_alphanumeric(15, start="domain_"),
        fauxfactory.gen_alphanumeric(15, start="domain_desc_"),
        enabled=True
    )
    yield domain
    if domain.exists:
        domain.delete()


@pytest.fixture
def catalog_item(appliance, provider, dialog, catalog, prov_data):

    collection = appliance.collections.catalog_items
    catalog_item = collection.create(provider.catalog_item_type,
                                     name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
                                     description='test catalog',
                                     display_in=True,
                                     catalog=catalog,
                                     dialog=dialog,
                                     prov_data=prov_data)
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


@pytest.fixture
def catalog_bundle(appliance, dialog, catalog, catalog_item):
    collection = appliance.collections.catalog_bundles
    catalog_bundle = collection.create(name=fauxfactory.gen_alphanumeric(15, start="cat_bundle_"),
                                       catalog_items=[catalog_item.name],
                                       description='test catalog bundle',
                                       display_in=True,
                                       catalog=catalog,
                                       dialog=dialog)

    yield catalog_bundle
    if catalog_bundle.exists:
        catalog_bundle.delete()


@pytest.fixture(scope='module')
def max_quota_test_instance(appliance, domain):
    miq = appliance.collections.domains.instantiate('ManageIQ')

    original_instance = (
        miq.namespaces.instantiate('System').
        namespaces.instantiate('CommonMethods').
        classes.instantiate('QuotaMethods').
        instances.instantiate('quota_source')
    )
    original_instance.copy_to(domain=domain)

    original_instance = (
        miq.namespaces.instantiate('System').
        namespaces.instantiate('CommonMethods').
        classes.instantiate('QuotaStateMachine').
        instances.instantiate('quota')
    )
    original_instance.copy_to(domain=domain)

    instance = (
        domain.namespaces.instantiate('System').
        namespaces.instantiate('CommonMethods').
        classes.instantiate('QuotaStateMachine').
        instances.instantiate('quota')
    )
    return instance


def set_entity_quota_source(max_quota_test_instance, entity):
    with update(max_quota_test_instance):
        max_quota_test_instance.fields = {'quota_source_type': {'value': entity}}


@pytest.fixture(params=[('groups', 'group', 'EvmGroup-super_administrator'),
                        ('users', 'user', 'Administrator')], ids=['group', 'user'], scope='module')
def entities(appliance, request, max_quota_test_instance):
    collection, entity, description = request.param
    set_entity_quota_source(max_quota_test_instance, entity)
    return getattr(appliance.collections, collection).instantiate(description)


@pytest.fixture(scope='function')
def set_entity_quota_tag(request, entities, appliance):
    tag, value = request.param
    tag = appliance.collections.categories.instantiate(
        display_name=tag).collections.tags.instantiate(
        display_name=value)
    entities.add_tag(tag)
    yield
    # will refresh page as navigation to configuration is blocked if alert are on requests page
    appliance.server.browser.refresh()
    entities.remove_tag(tag)


@pytest.mark.rhv2
@pytest.mark.parametrize(
    ['set_entity_quota_tag', 'custom_prov_data'],
    [
        [('Quota - Max Memory', '1GB'), {'hardware': {'memory': '4096'}}],
        [('Quota - Max Storage', '10GB'), {}],
        [('Quota - Max CPUs', '1'), {'hardware': {'num_sockets': '8'}}]
    ],
    indirect=['set_entity_quota_tag'],
    ids=['max_memory', 'max_storage', 'max_cpu']
)
def test_quota_tagging_infra_via_lifecycle(request, appliance, provider,
                                           set_entity_quota_tag, custom_prov_data,
                                           vm_name, template_name, prov_data):
    """

    Polarion:
        assignee: ghubale
        casecomponent: Quota
        caseimportance: medium
        initialEstimate: 1/6h
        tags: quota
    """
    recursive_update(prov_data, custom_prov_data)
    do_vm_provisioning(appliance, template_name=template_name, provider=provider, vm_name=vm_name,
                       provisioning_data=prov_data, wait=False, request=None)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{template}] to [{vm}]'.format(template=template_name,
                                                                         vm=vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


# Here set_entity_quota_tag is used for setting the tag value.
# Here custom_prov_data is used to provide the value fo the catalog item to be created.
@pytest.mark.rhv2
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_entity_quota_tag', 'custom_prov_data'],
    [
        [('Quota - Max Memory *', '1GB'), {'hardware': {'memory': '4096'}}],
        [('Quota - Max Storage *', '10GB'), {}],
        [('Quota - Max CPUs *', '1'), {'hardware': {'num_sockets': '8'}}]
    ],
    indirect=['set_entity_quota_tag'],
    ids=['max_memory', 'max_storage', 'max_cpu']
)
def test_quota_tagging_infra_via_services(request, appliance, admin_email, context,
                                          set_entity_quota_tag, custom_prov_data, prov_data,
                                          catalog_item):
    """This test case verifies the quota tagging is working correctly for the infra providers.

    Polarion:
        assignee: ghubale
        casecomponent: Quota
        caseimportance: medium
        initialEstimate: 1/6h
        tags: quota
    """

    prov_data.update(custom_prov_data)
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


@pytest.fixture(scope="module")
def small_vm(provider, small_template_modscope):
    vm = provider.appliance.collections.infra_vms.instantiate(
        random_vm_name(context="reconfig"), provider, small_template_modscope.name
    )
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()
    yield vm
    vm.cleanup_on_provider()


@pytest.fixture
def custom_prov_data(request, prov_data, vm_name, template_name):
    prov_data.update(request.param)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['catalog']['catalog_name'] = {'name': template_name}


@pytest.mark.long_running
@pytest.mark.parametrize(
    [
        "custom_prov_data",
        "processor_sockets",
        "processor_cores_per_socket",
        "total_processors",
        "approve",
    ],
    [
        [{"change": "cores_per_socket", "value": "4"}, "1", "4", "4", False],
        [{"change": "sockets", "value": "4"}, "4", "1", "4", False],
        [{"change": "mem_size", "value": "102400"}, "", "", "", True],
    ],
    indirect=["custom_prov_data"],
    ids=["max_cores", "max_sockets", "max_memory"],
)
def test_quota_vm_reconfigure(
    appliance,
    admin_email,
    entities,
    small_vm,
    custom_prov_data,
    prov_data,
    processor_sockets,
    processor_cores_per_socket,
    total_processors,
    approve,
):
    """Tests quota with vm reconfigure

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Quota
        caseimportance: high
        tags: quota
        testSteps:
            1. Assign Quota to group and user individually
            2. Reconfigure the VM above the assigned Quota
            3. Check whether VM  reconfiguration 'Denied' with Exceeded Quota or not
    """
    original_config = small_vm.configuration.copy()
    new_config = small_vm.configuration.copy()
    setattr(new_config.hw, prov_data["change"], prov_data["value"])
    small_vm.reconfigure(new_config)
    if approve:
        request_description = "VM Reconfigure for: {vm_name} - Memory: 102400 MB".format(
            vm_name=small_vm.name
        )
    else:
        request_description = (
            "VM Reconfigure for: {vm_name} - Processor Sockets: {sockets}, "
            "Processor Cores Per Socket: {cores_per_socket}, Total Processors: "
            "{Processors}".format(
                vm_name=small_vm.name,
                sockets=processor_sockets,
                cores_per_socket=processor_cores_per_socket,
                Processors=total_processors,
            )
        )
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method="ui")
    assert provision_request.row.reason.text == "Quota Exceeded"
    assert small_vm.configuration == original_config


@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['custom_prov_data'],
    [
        [{'hardware': {'memory': '4096'}}],
        [{}],
        [{'hardware': {'vm_num': '21'}}],
        [{'hardware': {'num_sockets': '8'}}]
    ],
    ids=['max_memory', 'max_storage', 'max_vm', 'max_cpu']
)
def test_quota_infra(request, appliance, admin_email, entities,
                     custom_prov_data, prov_data, catalog_item, context, vm_name, template_name):
    """This test case verifies the quota assigned by automation method for user and group
       is working correctly for the infra providers.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Quota
        caseimportance: medium
        tags: quota
        testSteps:
            1. Navigate to Automation > Automate > Explorer
            2. Add quota automation methods to domain
            3. Change 'quota_source_type' to 'user' or 'group'
            4. Test quota by provisioning VMs over quota limit via UI or SSUI for user and group
            5. Check whether quota is exceeded or not
    """
    prov_data.update(custom_prov_data)
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


@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['custom_prov_data'],
    [
        [{'hardware': {'memory': '4096'}}],
        [{}],  # This parameterization is for selecting storage while provisioning VM.
        # But it is not possible to parameterize storage size.
        # Because it is defined in disk formats(Thin, Thick, Default and other types).
        # Also it varies with providers.
        # But we don't need to select storage because by default storage is already more than
        # assigned storage quota which is 2GB maximum.
        [{'hardware': {'vm_num': '21'}}],
        [{'hardware': {'num_sockets': '8'}}]
    ],
    ids=['max_memory', 'max_storage', 'max_vm', 'max_cpu']
)
def test_quota_catalog_bundle_infra(request, appliance, admin_email, entities, custom_prov_data,
                                    prov_data, catalog_bundle, context, vm_name, template_name):
    """This test case verifies the quota assigned by automation method for user and group
       is working correctly for the infra providers by ordering catalog bundle.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Quota
        caseimportance: high
        tags: quota
        testSteps:
            1. Navigate to Automation > Automate > Explorer
            2. Add quota automation methods to domain
            3. Change 'quota_source_type' to 'user' or 'group'
            4. Create one or more catalogs to test quota by provisioning VMs over quota limit via UI
               or SSUI for user and group
            5. Add more than one catalog to catalog bundle and order catalog bundle
            6. Check whether quota is exceeded or not
    """
    prov_data.update(custom_prov_data)
    with appliance.context.use(context):
        service_catalogs = ServiceCatalogs(appliance, catalog_bundle.catalog, catalog_bundle.name)
        if context is ViaSSUI:
            service_catalogs.add_to_shopping_cart()
        service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = 'Provisioning Service [{0}] from [{0}]'.format(catalog_bundle.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"
