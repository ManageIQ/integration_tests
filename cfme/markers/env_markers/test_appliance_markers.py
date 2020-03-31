import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.utils.testgen import ALL
from cfme.utils.testgen import ONE


pytestmark = [
    pytest.mark.provider([InfraProvider], scope='module', selector=ONE),
    pytest.mark.appliance(['multi-region', 'pod'], scope='module'),
]


@pytest.mark.appliance(['default'], scope='function')
def test_one_app_type(appliance, provider):
    pass


def test_multiple_appliance_types(appliance, provider):
    pass


@pytest.mark.appliance(ALL, scope='function')
def test_all_appliance_types(appliance, provider):
    pass
