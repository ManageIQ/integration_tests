import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update

pytestmark = [
    test_requirements.quota,
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.provider([OpenStackProvider],
                         required_fields=[['provisioning', 'image']], scope="module")
]


@pytest.fixture
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
def template_name(provisioning):
    return provisioning["image"]["name"]


@pytest.fixture
def prov_data(provider, vm_name, template_name, provisioning):
    if provider.one_of(OpenStackProvider):
        return {
            "catalog": {"vm_name": vm_name, "catalog_name": {"name": template_name}},
            "environment": {"automatic_placement": True},
            "properties": {
                "instance_type": partial_match(
                    provisioning.get("instance_type2", "Instance type is not available")
                )
            },
        }


@pytest.fixture(scope='module')
def domain(appliance):
    domain = appliance.collections.domains.create(
        fauxfactory.gen_alphanumeric(start="domain_"),
        fauxfactory.gen_alphanumeric(15, start="domain_desc_"),
        enabled=True
    )
    yield domain
    if domain.exists:
        domain.delete()


@pytest.fixture
def catalog_item(appliance, provider, dialog, catalog, prov_data):
    collection = appliance.collections.catalog_items
    catalog_item = collection.create(
        provider.catalog_item_type,
        name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
        description='test catalog',
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        prov_data=prov_data)
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


@pytest.fixture(scope='module')
def max_quota_test_instance(appliance, domain):
    miq = appliance.collections.domains.instantiate('ManageIQ')

    original_instance = (
        miq.namespaces.instantiate('System')
        .namespaces.instantiate('CommonMethods')
        .classes.instantiate('QuotaMethods')
        .instances.instantiate('quota_source')
    )
    original_instance.copy_to(domain=domain)

    original_instance = (
        miq.namespaces.instantiate('System')
        .namespaces.instantiate('CommonMethods')
        .classes.instantiate('QuotaStateMachine')
        .instances.instantiate('quota')
    )
    original_instance.copy_to(domain=domain)

    instance = (
        domain.namespaces.instantiate('System')
        .namespaces.instantiate('CommonMethods')
        .classes.instantiate('QuotaStateMachine')
        .instances.instantiate('quota')
    )
    return instance


def set_entity_quota_source(max_quota_test_instance, entity):
    with update(max_quota_test_instance):
        max_quota_test_instance.fields = {'quota_source_type': {'value': entity}}


@pytest.fixture(params=['user', 'group'])
def set_entity_quota_source_change(max_quota_test_instance, request):
    entity_value = request.param
    with update(max_quota_test_instance):
        max_quota_test_instance.fields = {'quota_source_type': {'value': entity_value}}


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


@pytest.mark.parametrize(
    ['set_entity_quota_tag'],
    [
        [('Quota - Max Memory *', '1GB')],
        [('Quota - Max Storage *', '10GB')],
        [('Quota - Max CPUs *', '1')]
    ],
    indirect=['set_entity_quota_tag'],
    ids=['max_memory', 'max_storage', 'max_cpu']
)
def test_quota_tagging_cloud_via_lifecycle(request, appliance, provider, prov_data,
                                           set_entity_quota_tag, template_name, vm_name):
    """Test Group and User Quota in UI using tagging

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/6h
        tags: quota
    """
    recursive_update(prov_data, {
        'request': {'email': 'test_{}@example.com'.format(fauxfactory.gen_alphanumeric())}})
    prov_data.update({'template_name': template_name})
    appliance.collections.cloud_instances.create(vm_name, provider, prov_data, override=True)
    # nav to requests page to check quota validation
    request_description = 'Provision from [{template}] to [{vm}]'.format(template=template_name,
                                                                         vm=vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
@pytest.mark.parametrize(
    ['set_entity_quota_tag'],
    [
        [('Quota - Max Memory *', '1GB')],
        [('Quota - Max Storage *', '10GB')],
        [('Quota - Max CPUs *', '1')]
    ],
    indirect=['set_entity_quota_tag'],
    ids=['max_memory', 'max_storage', 'max_cpu']
)
def test_quota_tagging_cloud_via_services(appliance, request, context, admin_email,
                                          set_entity_quota_tag, catalog_item):
    """Test Group and User Quota in UI and SSUI using tagging

    Polarion:
        assignee: ghubale
        casecomponent: Cloud
        initialEstimate: 1/6h
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


def test_cloud_quota_by_lifecycle(request, appliance, provider, set_entity_quota_source_change,
                                  prov_data, vm_name, template_name):
    """Testing cloud quota for user and group by provisioning instance via lifecycle

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        tags: quota
        testSteps:
            1. Navigate to Automation > automate > Explorer
            2. Create new Domain and copy 'quota' and 'quota_source' method
            3. Change 'value' of 'open source type' to 'user' or 'group' (one by one) in 'quota'
               method
            4. Provision instance via lifecycle
            5. Make sure that provisioned 'template' is having more than assigned quota
            6. Check whether instance provision 'Denied' with reason 'Quota Exceeded'
    """
    recursive_update(prov_data, {
        'request': {'email': 'test_{}@example.com'.format(fauxfactory.gen_alphanumeric())}})
    prov_data.update({'template_name': template_name})
    appliance.collections.cloud_instances.create(vm_name, provider, prov_data, override=True)
    # nav to requests page to check quota validation
    request_description = 'Provision from [{template}] to [{vm}]'.format(template=template_name,
                                                                         vm=vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
def test_quota_cloud_via_services(appliance, request, admin_email, entities, prov_data,
                                  catalog_item, context):
    """This test case verifies the quota assigned by automation method for user and group
       is working correctly for the cloud providers.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/4h
        casecomponent: Cloud
        tags: quota
        testSteps:
           1. Navigate to Automation > Automate > Explorer
           2. Add quota automation methods to domain
           3. Change 'quota_source_type' to 'user' or 'group'
           4. Test quota by provisioning instances over quota limit via UI or
              SSUI for user and group
           5. Check whether quota is exceeded or not
    """
    with appliance.context.use(context):
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        if context is ViaSSUI:
            service_catalogs.add_to_shopping_cart()
        service_catalogs.order()
    # nav to requests page to check quota validation
    request_description = ("Provisioning Service [{catalog_item_name}] from [{catalog_item_name}]"
                           .format(catalog_item_name=catalog_item.name))
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"
