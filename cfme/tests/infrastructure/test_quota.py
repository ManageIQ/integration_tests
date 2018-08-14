# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from riggerlib import recursive_update

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update

pytestmark = [
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
def prov_data(vm_name):
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


@pytest.fixture(scope='module')
def new_tenant(appliance):
    tenant_list = []
    for i in range(0, 3):
        collection = appliance.collections.tenants
        tenant = collection.create(name='tenant{}'.format(fauxfactory.gen_alphanumeric()),
                                   description='tenant_des{}'.
                                   format(fauxfactory.gen_alphanumeric()),
                                   parent=collection.get_root_tenant())
        tenant_list.append(tenant)
    yield tenant_list
    if tenant.exists:
        tenant.delete()


@pytest.fixture
def set_parent_tenant_quota(request, appliance, new_tenant):
    for i in range(0, 3):
        field, value = request.param
        new_tenant[i].set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.login_admin()
    appliance.server.browser.refresh()
    for i in range(0, 3):
        new_tenant[i].set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture(scope='module')
def new_group_list(appliance, new_tenant):
    group_list = []
    collection = appliance.collections.groups
    for i in range(0, 3):
        group = collection.create(description='group_{}'.format(fauxfactory.gen_alphanumeric()),
                                  role='EvmRole-super_administrator',
                                  tenant='My Company/{}'.format(new_tenant[i].name))
        group_list.append(group)
    yield group_list
    if group.exists:
        group.delete()


@pytest.fixture(scope='module')
def new_user(appliance, new_group_list, new_credential):
    collection = appliance.collections.users
    user = collection.create(
        name='user_{}'.format(fauxfactory.gen_alphanumeric()),
        credential=new_credential,
        email='xyz@redhat.com',
        groups=new_group_list,
        cost_center='Workload',
        value_assign='Database')
    yield user


@pytest.fixture
def custom_prov_data(request, prov_data, vm_name, template_name):
    value = request.param
    prov_data.update(value)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['catalog']['catalog_name'] = {'name': template_name}


@pytest.mark.rhv2
# Here cust_prov_data is the dict required during provisioning of the VM.
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
def test_quota(appliance, provider, setup_provider, custom_prov_data, vm_name, admin_email,
               entities, template_name, prov_data):
    """This test case checks quota limit using the automate's predefine method 'quota source'"""
    recursive_update(prov_data, custom_prov_data)
    do_vm_provisioning(appliance, template_name=template_name, provider=provider, vm_name=vm_name,
                       provisioning_data=prov_data, smtp_test=False, wait=False, request=None)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.parametrize(
    ['set_parent_tenant_quota', 'custom_prov_data', 'extra_msg', 'approve'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, '', False],
        [('storage', '0.01'), {}, '', False],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, '', False],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_parent_tenant_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_user_quota_diff_groups(request, appliance, provider, setup_provider, new_user,
                                set_parent_tenant_quota, extra_msg, custom_prov_data, approve,
                                prov_data, vm_name, template_name):
    """prerequisite: Provider should be added

    steps:

    1. Create three tenants
    2. Create Three new groups
    3. Three groups should be assigned to three different tenants
    4. Create new user
    5. User should be member of three groups
    6. Assign quota for three tenants(like ('cpu', '2') for three tenants at a time)
    7. Provision VM with more than assigned quota
    """
    with new_user:
        recursive_update(prov_data, custom_prov_data)
        do_vm_provisioning(appliance, template_name=template_name, provider=provider,
                           vm_name=vm_name, provisioning_data=prov_data, smtp_test=False,
                           wait=False, request=None)

        # nav to requests page to check quota validation
        request_description = 'Provision from [{}] to [{}{}]'.format(template_name, vm_name,
                                                                     extra_msg)
        provision_request = appliance.collections.requests.instantiate(request_description)
        if approve:
            provision_request.approve_request(method='ui', reason="Approved")
        provision_request.wait_for_request(method='ui')
        assert provision_request.row.reason.text == "Quota Exceeded"
