import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.long_running,
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope="module",
                         required_fields=[["provisioning", "template"]], selector=ONE_PER_TYPE)
]


@pytest.fixture
def vm_name():
    return random_vm_name(context='quota')


@pytest.fixture
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture
def prov_data(vm_name, provisioning):
    return {
        "catalog": {'vm_name': vm_name},
        "environment": {'automatic_placement': True},
        "network": {'vlan': partial_match(provisioning['vlan'])}
    }


@pytest.fixture
def set_child_tenant_quota(request, appliance, new_child):
    field, value = request.param
    new_child.set_quota(**{f'{field}_cb': True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.login_admin()
    appliance.server.browser.refresh()
    new_child.set_quota(**{f'{field}_cb': False})


@pytest.fixture(scope='module')
def new_tenant(appliance):
    collection = appliance.collections.tenants
    tenant = collection.create(name=fauxfactory.gen_alphanumeric(15, start="tenant_"),
                               description=fauxfactory.gen_alphanumeric(15, start="tenant_desc_"),
                               parent=collection.get_root_tenant())
    yield tenant
    if tenant.exists:
        tenant.delete()


@pytest.fixture(scope='module')
def new_child(appliance, new_tenant):
    collection = appliance.collections.tenants
    child_tenant = collection.create(
        name=fauxfactory.gen_alphanumeric(15, start="tenant_"),
        description=fauxfactory.gen_alphanumeric(15, start="tenant_desc_"),
        parent=new_tenant
    )
    yield child_tenant
    if child_tenant.exists:
        child_tenant.delete()


@pytest.fixture(scope='module')
def new_group(appliance, new_child, new_tenant):
    collection = appliance.collections.groups
    group = collection.create(description=fauxfactory.gen_alphanumeric(start="group_"),
                              role='EvmRole-administrator',
                              tenant=f'My Company/{new_tenant.name}/{new_child.name}')
    yield group
    if group.exists:
        group.delete()


@pytest.fixture(scope='module')
def new_user(appliance, new_group, new_credential):
    collection = appliance.collections.users
    user = collection.create(
        name=fauxfactory.gen_alphanumeric(start="user_"),
        credential=new_credential,
        email=fauxfactory.gen_email(),
        groups=new_group,
        cost_center='Workload',
        value_assign='Database')
    yield user
    if user.exists:
        user.delete()


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_child_tenant_quota', 'custom_prov_data', 'extra_msg', 'approve'],
    [
        [('cpu', '2'), {'hardware': {'num_sockets': '8'}}, '', False],
        [('storage', '0.01'), {}, '', False],
        [('memory', '2'), {'hardware': {'memory': '4096'}}, '', False],
        [('vm', '1'), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_child_tenant_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_child_tenant_quota_enforce_via_lifecycle_infra(appliance, provider, new_user,
                                                        set_child_tenant_quota, extra_msg,
                                                        custom_prov_data, approve, prov_data,
                                                        vm_name, template_name):
    """Test child tenant feature via lifecycle method.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
        tags: quota
    """
    with new_user:
        recursive_update(prov_data, custom_prov_data)
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
