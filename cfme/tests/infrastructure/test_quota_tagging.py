# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.configure.configuration.region_settings import Tag, Category
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update

pytestmark = [
    pytest.mark.provider([RHEVMProvider, VMwareProvider], scope="module", selector=ONE_PER_TYPE)
]


@pytest.fixture
def vm_name():
    return random_vm_name(context='quota')


@pytest.fixture
def template_name(provider):
    if provider.one_of(RHEVMProvider):
        return provider.data.templates.get('full_template')['name']
    elif provider.one_of(VMwareProvider):
        return provider.data.templates.get('big_template')['name']


@pytest.fixture()
def prov_data(provider, vm_name):
    if provider.one_of(RHEVMProvider):
        return {
            "catalog": {'vm_name': vm_name},
            "environment": {'automatic_placement': True},
            "network": {'vlan': partial_match('ovirtmgmt')},
        }
    else:
        return {
            "catalog": {'vm_name': vm_name},
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
    yield instance


def set_entity_quota_source(max_quota_test_instance, entity):
    with update(max_quota_test_instance):
        max_quota_test_instance.fields = {'quota_source_type': {'value': entity}}


@pytest.fixture(params=[('groups', 'group', 'EvmGroup-super_administrator'),
                        ('users', 'user', 'Administrator')],
                ids=['group', 'user'],
                scope='module')
def entities(appliance, request, max_quota_test_instance):
    collection, entity, description = request.param
    set_entity_quota_source(max_quota_test_instance, entity)
    yield getattr(appliance.collections, collection).instantiate(description)


@pytest.fixture(scope='function')
def set_entity_quota_tag(request, entities, appliance):
    tag, value = request.param
    tag = Tag(display_name=value, category=Category(display_name=tag))
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
def test_quota_tagging(appliance, provider, setup_provider, set_entity_quota_tag, custom_prov_data,
                       vm_name, template_name, prov_data):
    """Tests quota tagging

    Metadata:
        test_flag: quota
    """
    recursive_update(prov_data, custom_prov_data)

    do_vm_provisioning(appliance, template_name=template_name, provider=provider, vm_name=vm_name,
                       provisioning_data=prov_data, smtp_test=False, wait=False, request=None)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"
