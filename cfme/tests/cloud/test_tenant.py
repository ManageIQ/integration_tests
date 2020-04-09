import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.update import update

pytestmark = [pytest.mark.provider([OpenStackProvider], scope='module')]

# List of tenant's names
TENANTS = [
    fauxfactory.gen_alphanumeric(start="parent_"),
    fauxfactory.gen_alphanumeric(start="child_")
]


@pytest.fixture(scope='function')
def tenant(provider, setup_provider, appliance):
    tenant = appliance.collections.cloud_tenants.create(
        name=fauxfactory.gen_alphanumeric(start="tenant_"),
        provider=provider
    )
    yield tenant

    try:
        if tenant.exists:
            tenant.delete()
    except Exception:
        logger.warning(
            'Exception while attempting to delete tenant fixture, continuing')
    finally:
        if tenant.name in provider.mgmt.list_tenant():
            provider.mgmt.remove_tenant(tenant.name)


@test_requirements.multi_tenancy
def test_tenant_crud(tenant):
    """ Tests tenant create and delete

    Metadata:
        test_flag: tenant

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Cloud
    """

    with update(tenant):
        tenant.name = fauxfactory.gen_alphanumeric(15, start="edited_")
    tenant.wait_for_appear()
    assert tenant.exists


@pytest.fixture(scope="module")
def new_tenant(appliance):
    """This fixture creates new tenant under root tenant(My Company)"""
    collection = appliance.collections.tenants

    # Here TENANT[0] is the first tenant(parent tenant) from the tenant's list
    tenant = collection.create(
        name=TENANTS[0],
        description=fauxfactory.gen_alphanumeric(15, start="tenant_desc_"),
        parent=collection.get_root_tenant(),
    )
    yield tenant
    tenant.delete_if_exists()


@pytest.fixture(scope="module")
def child_tenant(new_tenant):
    """This fixture used to create child tenant under parent tenant - new_tenant"""
    # Here TENANT[1] is the second tenant(child tenant) from the tenant's list
    child_tenant = new_tenant.appliance.collections.tenants.create(
        name=TENANTS[1],
        description=fauxfactory.gen_alphanumeric(15, start="tenant_desc_"),
        parent=new_tenant,
    )
    yield child_tenant
    child_tenant.delete_if_exists()


def check_permissions(appliance, assigned_tenant):
    """This function is used to check user permissions for particular tenant"""
    view = navigate_to(appliance.collections.tenants, 'All')
    # TODO(GH-8662): Need to restructure tenant entity by considering RBAC roles
    for tenant in view.table:
        if tenant["Name"].text == assigned_tenant:
            tenant.click()
            break
    assert not view.toolbar.configuration.has_item('Manage Quotas')


@test_requirements.quota
@pytest.mark.tier(1)
def test_dynamic_product_feature_for_tenant_quota(request, appliance, new_tenant, child_tenant):
    """
    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/12h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Configuration
        tags: quota
        testSteps:
            1. Add two users > alpha and omega
            2. Create two tenants > alpha_tenant and it's child - omega_tenant
            3. Create two custom roles (role_alpha and role_omega) from copying
               EvmRole-tenant-administrator role
            4. Create groups alpha_group(for alpha_tenant) and omega_group(for omega_tenant)
               then assign role_alpha to alpha_group and role_omega to omega_group
            5. Add alpha_group to alpha user and omega_group to omega user
            6. Modify role_alpha for manage quota permissions of alpha user as it will manage
               only quota of omega_tenant
            7. Modify role_omega for manage quota permissions of omega user as it will not even
               manage quota of itself or other tenants
            8. CHECK IF YOU ARE ABLE TO MODIFY THE "MANAGE QUOTA" CHECKS IN ROLE AS YOU WANT
            9. Then see if you are able to save these two new roles.
            10.Login with alpha and SEE IF ALPHA USER CAN ABLE TO SET QUOTA OF omega_tenant
            11.Login with omega and SEE QUOTA GETS CHANGED OR NOT. THEN TRY TO CHANGE QUOTA
               IMPOSED BY ALPHA USER.
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7.
            8.
            9. Save roles successfully
            10. 'Manage Quotas' option should be available for user alpha
            11. Here as per role_omega permissions, omega must not able change its own quota or
                 other tenants quota.

    Bugzilla:
        1655012
        1468795
    """
    user_ = []
    role_ = []

    # Tree path navigation(for quota management permissions) to particular node of product feature
    # in RBAC for roles
    product_feature = ['Everything']
    product_feature.extend(
        ['Settings', 'Configuration'] if appliance.version < '5.11' else ['Main Configuration'])
    product_feature.extend(["Access Control", "Tenants", "Modify", "Manage Quotas"])

    # List of two tenants with their parents to assign to two different groups
    tenant_ = [f"My Company/{new_tenant.name}",
               "My Company/{parent}/{child}".format(parent=new_tenant.name,
                                                    child=child_tenant.name)]

    # Instantiating existing role - 'EvmRole-tenant_administrator' to copy it to new role
    role = appliance.collections.roles.instantiate(name='EvmRole-tenant_administrator')
    for i in range(2):
        # Creating two different RBAC roles for two different users
        new_role = role.copy(name="{name}_{role}".format(name=role.name,
                                                         role=fauxfactory.gen_alphanumeric()))
        role_.append(new_role)
        request.addfinalizer(new_role.delete_if_exists)

        # Creating two different groups with assigned custom roles and tenants
        group = appliance.collections.groups.create(
            description=fauxfactory.gen_alphanumeric(start="group_"),
            role=new_role.name,
            tenant=tenant_[i]
        )
        request.addfinalizer(group.delete_if_exists)

        # Creating two different users which are assigned with different groups
        user = appliance.collections.users.create(
            name=fauxfactory.gen_alphanumeric(start="user_").lower(),
            credential=Credential(
                principal=fauxfactory.gen_alphanumeric(start="uid"),
                secret=fauxfactory.gen_alphanumeric(start="pwd_"),
            ),
            email=fauxfactory.gen_email(),
            groups=group,
            cost_center="Workload",
            value_assign="Database",
        )
        user_.append(user)
        request.addfinalizer(user.delete_if_exists)

        # Updating roles for users with product_feature tree. It restrict user from the
        # tenants for which this role does not have access.
        # Here product_feature is the tree path navigation for updating RBAC role for tenant1 -
        # (parent tenant) and tenant2 - (child tenant) from TENANTS list.
        # role_[0] and role_[1] is the first and second role from the list of two role created
        # above; Providing 'False' while updating role means it restrict user from accessing that
        # particular tenant.
        product_feature.extend(["Manage Quotas ({tenant})".format(tenant=TENANTS[i])])
        role_[i].update({'product_features': [(product_feature, False)]})
        # Need to pop up last element added which is parent tenant. So that we can add child tenant
        # for updating product feature for it.
        product_feature.pop()

    # Logged in with user1 and then checking; this user should not have access of manage quota for
    # tenant1(parent tenant).
    with user_[0]:
        check_permissions(appliance=appliance, assigned_tenant=new_tenant.name)

    # Logged in with user2 and then checking; this user should not have access of manage quota for
    # tenant2(child tenant).
    with user_[1]:
        check_permissions(appliance=appliance, assigned_tenant=child_tenant.name)


@test_requirements.quota
@pytest.mark.tier(2)
def test_tenant_quota_input_validate(appliance):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/8h
    """
    roottenant = appliance.collections.tenants.get_root_tenant()
    fields = [('cpu', 2.5), ('storage', '1.x'), ('memory', '2.x'), ('vm', 1.5)]

    for field in fields:
        view = navigate_to(roottenant, 'ManageQuotas')
        # Enforcing quota for 'My Company' tenant. For example: To put the values of vm quota. It
        # needs Enforced - True for 'Allocated Number of Virtual Machines'('vm_cb': True) which
        # enables the value field('vm_txt': 1.5)
        view.form.fill({'{}_cb'.format(field[0]): True, '{}_txt'.format(field[0]): field[1]})
        assert view.save_button.disabled
        # Clean-up of enforced quota
        view.form.fill({'{}_cb'.format(field[0]): False})
