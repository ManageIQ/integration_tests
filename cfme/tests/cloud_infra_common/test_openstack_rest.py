import pytest
from cfme.cloud.provider.openstack import OpenStackProvider

pytestmark = [
    pytest.mark.provider(classes=[OpenStackProvider]),
    pytest.mark.provider(classes=[OpenStackProvider], fixture_name="second_provider"),
]


def test_something(provider, second_provider):
    provider.create_rest()
    second_provider.create_rest()
