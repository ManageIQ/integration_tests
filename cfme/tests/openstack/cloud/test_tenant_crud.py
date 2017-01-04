import pytest
from fauxfactory import gen_alphanumeric
import cfme.fixtures.pytest_selenium as sel
from cfme.cloud.tenant import Tenant
from utils.wait import wait_for


@pytest.mark.usefixtures("setup_provider_modscope")
def test_create_cloud_tenant(provider):
    """
        create a new cloud tenant
    """
    tenant_name = gen_alphanumeric()
    cloud_provider = provider.name
    new_tenant = Tenant(tenant_name, "A test cloud tenant", cloud_provider)
    new_tenant.create(cloud_provider)
    wait_for(provider.is_refreshed, [None, 10], delay=5)
    sel.refresh()
    assert new_tenant.exists(), "New cloud tenant hasn't been created"


@pytest.mark.usefixtures("setup_provider_modscope")
def test_update_cloud_tenant(cloud_tenant_name, new_tenant_name, cloud_provider):
    my_tenant = Tenant(cloud_tenant_name, "", cloud_provider)
    my_tenant.update(cloud_provider, new_tenant_name)
    wait_for(cloud_provider.is_refreshed, [None, 10], delay=5)
    sel.refresh()
    my_new_cloud_tenant = Tenant(new_tenant_name, "updated cloud tenant", cloud_provider)
    assert my_new_cloud_tenant.exists(), "Cloud tenant hasn't been updated"


@pytest.mark.usefixtures("setup_provider_modscope")
def test_delete_cloud_tenant(cloud_tenant):
    pass
