"""tests for Openstack cloud Keypairs"""

import fauxfactory
import pytest

from cfme.cloud.provider.openstack import OpenStackProvider


pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], scope='function')
]


@pytest.fixture(scope='function')
def keypair(appliance, provider):
    keypair = appliance.collections.cloud_keypairs.create(name=fauxfactory.gen_alphanumeric(),
                                                          provider=provider)
    yield keypair
    if keypair.exists:
        keypair.delete(wait=False)


@pytest.mark.rfe
@pytest.mark.ignore_stream('5.9')
def test_download_private_key(keypair):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    assert keypair.exists
    keypair.download_private_key()
