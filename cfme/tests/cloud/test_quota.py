# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.blockers import GH
from cfme.utils.appliance import current_appliance
from cfme.utils.generators import random_vm_name

pytestmark = [
    test_requirements.quota,
    pytest.mark.long_running,
    pytest.mark.provider([AzureProvider, OpenStackProvider],
                         required_fields=[['provisioning', 'image']], scope="module")
]


@pytest.fixture
def vm_name():
    return random_vm_name(context='quota')


@pytest.fixture
def template_name(provisioning):
    return provisioning["image"]["name"]


@pytest.fixture(scope="module")
def roottenant(appliance):
    return appliance.collections.tenants.get_root_tenant()


@pytest.fixture
def prov_data(provider, provisioning, vm_name):
    if provider.one_of(OpenStackProvider):
        return {
            "catalog": {'vm_name': vm_name},
            "environment": {'automatic_placement': True},
            "properties": {'instance_type': partial_match('m1.large')}
        }
    if provider.one_of(AzureProvider):
        return {
            "catalog": {'vm_name': vm_name},
            "environment": {'automatic_placement': True},
            "properties": {'instance_type': partial_match('d2s_v3')},
            "customize": {'admin_username': provisioning['customize_username'],
                          'root_password': provisioning['customize_password']}
        }


@pytest.fixture
def set_child_tenant_quota(request, appliance, new_child):
    field, value = request.param
    new_child.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.login_admin()
    appliance.server.browser.refresh()
    new_child.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture
def set_project_quota(request, appliance, new_project):
    field, value = request.param
    new_project.set_quota(**{'{}_cb'.format(field): True, field: value})
    yield
    # will refresh page as navigation to configuration is blocked if alerts are on the page
    appliance.server.login_admin()
    appliance.server.browser.refresh()
    new_project.set_quota(**{'{}_cb'.format(field): False})


@pytest.fixture(scope='module')
def new_tenant(appliance):
    collection = appliance.collections.tenants
    tenant = collection.create(name='tenant{}'.format(fauxfactory.gen_alphanumeric()),
                               description='tenant_des{}'.format(fauxfactory.gen_alphanumeric()),
                               parent=collection.get_root_tenant())
    yield tenant
    if tenant.exists:
        tenant.delete()


@pytest.fixture(scope='module')
def new_child(appliance, new_tenant):
    """The fist child tenant doesn't act like child tenant but equivale"""
    collection = appliance.collections.tenants
    child_tenant = collection.create(name='tenant{}'.format(fauxfactory.gen_alphanumeric()),
                                     description='tenant_des{}'.format(
                                         fauxfactory.gen_alphanumeric()),
                                     parent=new_tenant)
    yield child_tenant
    if child_tenant.exists:
        child_tenant.delete()


@pytest.fixture(scope='module')
def new_group_child(appliance, new_child, new_tenant):
    collection = appliance.collections.groups
    group = collection.create(description='group_{}'.format(fauxfactory.gen_alphanumeric()),
                              role='EvmRole-super_administrator',
                              tenant='My Company/{}/{}'.format(new_tenant.name, new_child.name))
    yield group
    if group.exists:
        group.delete()


@pytest.fixture(scope='function')
def new_user_child(appliance, new_group_child, new_credential):
    collection = appliance.collections.users
    user = collection.create(
        name='user_{}'.format(fauxfactory.gen_alphanumeric()),
        credential=new_credential,
        email='xyz@redhat.com',
        groups=new_group_child,
        cost_center='Workload',
        value_assign='Database')
    yield user
    if user.exists:
        user.delete()


@pytest.fixture(scope='module')
def new_project(appliance):
    collection = appliance.collections.projects
    project = collection.create(name='project{}'.format(fauxfactory.gen_alphanumeric()),
                                description='project_des{}'.format(fauxfactory.gen_alphanumeric()),
                                parent=collection.get_root_tenant())
    yield project
    if project.exists:
        project.delete()


@pytest.fixture(scope='module')
def new_group_project(appliance, new_project):
    collection = appliance.collections.groups
    group = collection.create(description='group_{}'.format(fauxfactory.gen_alphanumeric()),
                              role='EvmRole-super_administrator',
                              tenant='My Company/{}'.format(new_project.name))
    yield group
    if group.exists:
        group.delete()


@pytest.fixture(scope='function')
def new_user_project(appliance, new_group_project, new_credential):
    collection = appliance.collections.users
    user = collection.create(
        name='user_{}'.format(fauxfactory.gen_alphanumeric()),
        credential=new_credential,
        email='xyz@redhat.com',
        groups=new_group_project,
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
        [('cpu', 1), {}, '', False],
        [('storage', 0.001), {}, '', False],
        [('memory', 2), {}, '', False],
        [('vm', 1), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_child_tenant_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
@pytest.mark.meta(blockers=[GH('ManageIQ/integration_tests:7385',
                               unblock=lambda appliance_version:current_appliance.version < '5.9')])
def test_child_tenant_quota_enforce_via_lifecycle_cloud(request, appliance, provider,
                                                        setup_provider, new_user_child,
                                                        set_child_tenant_quota, extra_msg, approve,
                                                        custom_prov_data, prov_data, vm_name,
                                                        template_name):
    """Test Child Quota in UI"""
    with new_user_child:
        recursive_update(prov_data, custom_prov_data)
        recursive_update(prov_data, {
            'request': {'email': 'test_{}@example.com'.format(fauxfactory.gen_alphanumeric())}})
        prov_data.update({'template_name': template_name})
        request_description = 'Provision from [{}] to [{}{}]'.format(template_name, vm_name,
                                                                     extra_msg)
        appliance.collections.cloud_instances.create(vm_name, provider, prov_data,
                                                     auto_approve=approve,
                                                     override=True,
                                                     request_description=request_description)
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        assert provision_request.row.reason.text == "Quota Exceeded"

        request.addfinalizer(provision_request.remove_request)


# first arg of parametrize is the list of fixtures or parameters,
# second arg is a list of lists, with each one a test is to be generated
# sequence is important here
# indirect is the list where we define which fixtures are to be passed values indirectly.
@pytest.mark.parametrize(
    ['set_project_quota', 'custom_prov_data', 'extra_msg', 'approve'],
    [
        [('cpu', 1), {}, '', False],
        [('storage', 0.001), {}, '', False],
        [('memory', 2), {}, '', False],
        [('vm', 1), {'catalog': {'num_vms': '4'}}, '###', True]
    ],
    indirect=['set_project_quota'],
    ids=['max_cpu', 'max_storage', 'max_memory', 'max_vms']
)
def test_project_quota_enforce_via_lifecycle_cloud(request, appliance, provider, setup_provider,
                                                   new_user_project, set_project_quota, extra_msg,
                                                   approve, custom_prov_data, prov_data, vm_name,
                                                   template_name):
    """Test Project Quota in UI"""
    with new_user_project:
        recursive_update(prov_data, custom_prov_data)
        recursive_update(prov_data, {
            'request': {'email': 'test_{}@example.com'.format(fauxfactory.gen_alphanumeric())}})
        prov_data.update({'template_name': template_name})
        request_description = 'Provision from [{}] to [{}{}]'.format(template_name, vm_name,
                                                                     extra_msg)
        appliance.collections.cloud_instances.create(vm_name, provider, prov_data,
                                                     auto_approve=approve,
                                                     override=True,
                                                     request_description=request_description)
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        assert provision_request.row.reason.text == "Quota Exceeded"

        request.addfinalizer(provision_request.remove_request)
