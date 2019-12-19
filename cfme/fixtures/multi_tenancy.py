"""
Fixtures for Multi Tenancy
"""
import fauxfactory
import pytest

from cfme.base.credential import Credential
from cfme.utils.update import update


@pytest.fixture(scope='module')
def child_tenant(appliance):
    child_tenant = appliance.collections.tenants.create(
        name=fauxfactory.gen_alphanumeric(15, start="child_tenant_"),
        description='tenant description',
        parent=appliance.collections.tenants.get_root_tenant()
    )
    yield child_tenant
    child_tenant.delete_if_exists()


@pytest.fixture(scope='module')
def tenant_role(appliance, request):
    role = appliance.collections.roles.instantiate(name='EvmRole-tenant_administrator')
    tenant_role = role.copy()

    # Note: BZ 1278484 - tenant admin role has no permissions to create new roles
    with update(tenant_role):
        if appliance.version < '5.11':
            tenant_role.product_features = [
                (['Everything', 'Settings', 'Configuration', 'Settings'], True),
                (['Everything', 'Compute', 'Clouds', 'Auth Key Pairs'], True)
            ]
        else:
            tenant_role.product_features = [
                (['Everything', 'Main Configuration', 'Settings'], True),
                (['Everything', 'Compute', 'Clouds', 'Auth Key Pairs'], True)
            ]
    yield tenant_role
    tenant_role.delete_if_exists()


@pytest.fixture(scope='module')
def new_tenant_admin(appliance, request, child_tenant, tenant_role):
    credential = Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
                    secret='redhat')
    group = appliance.collections.groups.create(
        description=fauxfactory.gen_alphanumeric(15, start="tenant_grp_"), role=tenant_role.name,
        tenant=f'My Company/{child_tenant.name}')

    tenant_admin = appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric(start='tenant_admin_user'),
        credential=credential,
        email='xyz@redhat.com',
        groups=group,
        cost_center='Workload',
        value_assign='Database')
    yield tenant_admin
    tenant_admin.delete_if_exists()
    group.delete_if_exists()
