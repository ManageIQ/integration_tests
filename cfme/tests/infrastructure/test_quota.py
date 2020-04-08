import fauxfactory
import pytest
from riggerlib import recursive_update

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.update import update

pytestmark = [
    test_requirements.quota,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([RHEVMProvider, VMwareProvider], scope="module", selector=ONE_PER_TYPE)
]

NUM_GROUPS = NUM_TENANTS = 3


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
def prov_data(vm_name):
    return {
        "catalog": {'vm_name': vm_name},
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


@pytest.fixture(scope='module')
def max_quota_test_instance(appliance, domain):
    miq = appliance.collections.domains.instantiate('ManageIQ')

    original_instance = miq. \
        namespaces.instantiate('System'). \
        namespaces.instantiate('CommonMethods'). \
        classes.instantiate('QuotaMethods'). \
        instances.instantiate('quota_source')
    original_instance.copy_to(domain=domain)

    original_instance = miq. \
        namespaces.instantiate('System'). \
        namespaces.instantiate('CommonMethods'). \
        classes.instantiate('QuotaStateMachine'). \
        instances.instantiate('quota')
    original_instance.copy_to(domain=domain)

    instance = domain. \
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
    """Fixture is used to Create three tenants.
    """
    tenant_list = []
    for i in range(0, NUM_TENANTS):
        collection = appliance.collections.tenants
        tenant = collection.create(
            name=fauxfactory.gen_alphanumeric(15, start="tenant_"),
            description=fauxfactory.gen_alphanumeric(15, start="tenant_desc_"),
            parent=collection.get_root_tenant()
        )
        tenant_list.append(tenant)
    yield tenant_list
    for tnt in tenant_list:
        if tnt.exists:
            tnt.delete()


@pytest.fixture
def set_parent_tenant_quota(request, appliance, new_tenant):
    """Fixture is used to set tenant quota one by one to each of the tenant in 'new_tenant' list.
    After testing quota(example: testing cpu limit) with particular user and it's current group
    which is associated with one of these tenants. Then it disables the current quota
    (example: cpu limit) and enable new quota limit(example: Max memory) for testing.
    """
    for i in range(0, NUM_TENANTS):
        field, value = request.param
        new_tenant[i].set_quota(**{f'{field}_cb': True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.login_admin()
    appliance.server.browser.refresh()
    for i in range(0, NUM_TENANTS):
        new_tenant[i].set_quota(**{f'{field}_cb': False})


@pytest.fixture(scope='module')
def new_group_list(appliance, new_tenant):
    """Fixture is used to Create Three new groups and assigned to three different tenants.
    """
    group_list = []
    collection = appliance.collections.groups
    for i in range(0, NUM_GROUPS):
        group = collection.create(description=fauxfactory.gen_alphanumeric(start="group_"),
                                  role='EvmRole-super_administrator',
                                  tenant='My Company/{}'.format(new_tenant[i].name))
        group_list.append(group)
    yield group_list
    for grp in group_list:
        if grp.exists:
            grp.delete()


@pytest.fixture(scope='module')
def new_user(appliance, new_group_list, new_credential):
    """Fixture is used to Create new user and User should be member of three groups.
    """
    collection = appliance.collections.users
    user = collection.create(
        name=fauxfactory.gen_alphanumeric(start="user_"),
        credential=new_credential,
        email=fauxfactory.gen_email(),
        groups=new_group_list,
        cost_center='Workload',
        value_assign='Database')
    yield user
    if user.exists:
        user.delete()


@pytest.fixture
def custom_prov_data(request, prov_data, vm_name, template_name):
    value = request.param
    prov_data.update(value)
    prov_data['catalog']['vm_name'] = vm_name
    prov_data['catalog']['catalog_name'] = {'name': template_name}


# Here custom_prov_data is the dict required during provisioning of the VM.
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
def test_quota(appliance, provider, custom_prov_data, vm_name, admin_email, entities, template_name,
               prov_data):
    """This test case checks quota limit using the automate's predefine method 'quota source'

    Polarion:
        assignee: tpapaioa
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
def test_user_quota_diff_groups(appliance, provider, new_user, set_parent_tenant_quota, extra_msg,
                                custom_prov_data, approve, prov_data, vm_name, template_name):
    """
    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Quota
        caseimportance: high
        tags: quota
    """
    with new_user:
        recursive_update(prov_data, custom_prov_data)
        logger.info("Successfully updated VM provisioning data")
        do_vm_provisioning(appliance, template_name=template_name, provider=provider,
                           vm_name=vm_name, provisioning_data=prov_data, wait=False, request=None)

        # nav to requests page to check quota validation
        request_description = 'Provision from [{template}] to [{vm}{msg}]'.format(
            template=template_name, vm=vm_name, msg=extra_msg)
        provision_request = appliance.collections.requests.instantiate(request_description)
        if approve:
            provision_request.approve_request(method='ui', reason="Approved")
        provision_request.wait_for_request(method='ui')
        assert provision_request.row.reason.text == "Quota Exceeded"
