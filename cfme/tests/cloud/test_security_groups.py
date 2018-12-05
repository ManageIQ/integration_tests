import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.wait import TimedOutError

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([OpenStackProvider], scope="module")
]


@pytest.fixture(scope='module')
def sec_group(appliance, provider):
    collection = appliance.collections.security_groups
    try:
        sec_group = collection.create(name=fauxfactory.gen_alphanumeric(),
                                      description=fauxfactory.gen_alphanumeric(),
                                      provider=provider,
                                      wait=True)
    except TimedOutError:
        pytest.fail('Timed out creating Security Groups')
    yield sec_group
    if sec_group.exists:
        sec_group.delete(wait=True)


@pytest.mark.tier(3)
def test_security_group_crud(sec_group):
    """ This will test whether it will create new Security Group and then deletes it.
    Steps:
        * Select Network Manager.
        * Provide Security groups name.
        * Provide Security groups Description.
        * Select Cloud Tenant.
        * Also delete it.

    Polarion:
        assignee: None
        initialEstimate: None
    """
    # TODO: Update need to be done in future.
    assert sec_group.exists
    sec_group.delete(wait=True)
    assert not sec_group.exists


@pytest.mark.tier(3)
def test_security_group_create_cancel(appliance, provider):
    """ This will test cancelling on adding a security groups.

    Steps:
        * Select Network Manager.
        * Provide Security groups name.
        * Provide Security groups Description.
        * Select Cloud Tenant.
        * Cancel it.

    Polarion:
        assignee: None
        initialEstimate: None
    """
    security_group = appliance.collections.security_groups
    sec_group = security_group.create(name=fauxfactory.gen_alphanumeric(),
                                      description=fauxfactory.gen_alphanumeric(),
                                      provider=provider,
                                      cancel=True)
    assert not sec_group.exists
