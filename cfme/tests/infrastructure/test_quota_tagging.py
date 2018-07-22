# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance import ViaSSUI, ViaUI
from cfme.utils.blockers import GH
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update


pytestmark = [
    pytest.mark.meta(blockers=[GH('ManageIQ/integration_tests:7479')]),
    pytest.mark.provider([RHEVMProvider, VMwareProvider], scope="module", selector=ONE_PER_TYPE)
]


@pytest.fixture(scope='module')
def admin_email(appliance):
    """Required for user quota tagging services to work, as it's mandatory for it's functioning."""
    user = appliance.collections.users
    admin = user.instantiate(name='Administrator')
    with update(admin):
        admin.email = 'xyz@redhat.com'
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
def test_domain(appliance):
    domain = appliance.collections.domains.create('test_{}'.format(fauxfactory.gen_alphanumeric()),
                                                  'description_{}'.format(
                                                      fauxfactory.gen_alphanumeric()),
                                                  enabled=True)
    yield domain
    if domain.exists:
        domain.delete()


@pytest.fixture
def catalog_item(appliance, provider, dialog, catalog, prov_data):

    collection = appliance.collections.catalog_items
    catalog_item = collection.create(provider.catalog_item_type,
                                     name='test_{}'.format(fauxfactory.gen_alphanumeric()),
                                     description='test catalog',
                                     display_in=True,
                                     catalog=catalog,
                                     dialog=dialog,
                                     prov_data=prov_data)
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


@pytest.fixture(scope='module')
def max_quota_test_instance(appliance, test_domain):
    miq = appliance.collections.domains.instantiate('ManageIQ')

    original_instance = miq. \
        namespaces.instantiate('System'). \
        namespaces.instantiate('CommonMethods'). \
        classes.instantiate('QuotaMethods'). \
        instances.instantiate('quota_source')
    original_instance.copy_to(domain=test_domain)

    original_instance = miq. \
        namespaces.instantiate('System'). \
        namespaces.instantiate('CommonMethods'). \
        classes.instantiate('QuotaStateMachine'). \
        instances.instantiate('quota')
    original_instance.copy_to(domain=test_domain)

    instance = test_domain. \
        namespaces.instantiate('System'). \
        namespaces.instantiate('CommonMethods'). \
        classes.instantiate('QuotaStateMachine'). \
        instances.instantiate('quota')
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
def test_quota_tagging_infra_via_lifecycle(request, appliance, provider, setup_provider,
                                           set_entity_quota_tag, custom_prov_data,
                                           vm_name, template_name, prov_data):
    recursive_update(prov_data, custom_prov_data)
    do_vm_provisioning(appliance, template_name=template_name, provider=provider, vm_name=vm_name,
                       provisioning_data=prov_data, smtp_test=False, wait=False, request=None)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.rhv2
@pytest.mark.parametrize('context', [ViaSSUI, ViaUI])
# Here set_entity_quota_tag is used for setting the tag value.
# Here custom_prov_data is used to provide the value fo the catalog item to be created.
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
def test_quota_tagging_infra_via_services(request, appliance, provider, setup_provider, admin_email,
                                          context, set_entity_quota_tag, custom_prov_data,
                                          prov_data, catalog_item):
    """This test case verifies the quota tagging is working correctly for the infra providers."""

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
