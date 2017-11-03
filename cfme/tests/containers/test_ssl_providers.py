from collections import namedtuple
from copy import copy

from fauxfactory import gen_alphanumeric, gen_integer
import pytest

from cfme.containers.provider import ContainersProvider
from cfme.exceptions import FlashMessageException
from cfme.utils.version import current_version
from cfme.common.provider_views import ContainerProvidersView


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.8.0.3"),
    pytest.mark.provider([ContainersProvider], scope='module')
]

alphanumeric_name = gen_alphanumeric(10)
long_alphanumeric_name = gen_alphanumeric(100)
integer_name = str(gen_integer(0, 100000000))
provider_names = alphanumeric_name, integer_name, long_alphanumeric_name
DEFAULT_SEC_PROTOCOLS = (
    pytest.mark.polarion('CMP-10598')('SSL trusting custom CA'),
    pytest.mark.polarion('CMP-10597')('SSL without validation'),
    pytest.mark.polarion('CMP-10599')('SSL')
)

checked_item = namedtuple('TestItem', ['default_sec_protocol', 'hawkular_sec_protocol'])
TEST_ITEMS = (
    pytest.mark.polarion('CMP-10593')
    (checked_item('SSL trusting custom CA', 'SSL trusting custom CA')),
    pytest.mark.polarion('CMP-10594')
    (checked_item('SSL trusting custom CA', 'SSL without validation')),
    pytest.mark.polarion('CMP-10589')
    (checked_item('SSL trusting custom CA', 'SSL')),
    pytest.mark.polarion('CMP-10595')
    (checked_item('SSL without validation', 'SSL trusting custom CA')),
    pytest.mark.polarion('CMP-10596')
    (checked_item('SSL without validation', 'SSL without validation')),
    pytest.mark.polarion('CMP-10590')
    (checked_item('SSL without validation', 'SSL')),
    pytest.mark.polarion('CMP-10588')
    (checked_item('SSL', 'SSL trusting custom CA')),
    pytest.mark.polarion('CMP-10592')
    (checked_item('SSL', 'SSL without validation')),
    pytest.mark.polarion('CMP-10588')
    (checked_item('SSL', 'SSL')),
)


@pytest.mark.polarion('CMP-9836')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_add_provider_naming_conventions(provider, appliance, soft_assert):
    """" This test is checking ability to add Providers with different names:

    Steps:
        * Navigate to Containers Menu
        * Navigate to Add Provider Menu
        * Try to add a Container Provider with each of the following generated names:
            - Alphanumeric name
            - Long Alphanumeric name
            - Integer name
        * Assert that provider was added successfully with each of those
    """
    for provider_name in provider_names:
        new_provider = copy(provider)
        new_provider.name = provider_name
        new_provider.endpoints['default'].sec_protocol = 'SSL'
        try:
            new_provider.setup()
            view = appliance.browser.create_view(ContainerProvidersView)
            view.flash.assert_success_message(
                'Containers Providers "' + provider_name + '" was saved')
        except FlashMessageException:
            soft_assert(False, provider_name + ' wasn\'t added successfully')
        ContainersProvider.clear_providers()


@pytest.mark.parametrize('default_sec_protocol', DEFAULT_SEC_PROTOCOLS)
@pytest.mark.usefixtures('has_no_containers_providers')
def test_add_provider_ssl(provider, default_sec_protocol, soft_assert):
    """ This test checks adding container providers with 3 different security protocols:
    SSL trusting custom CA, SSL without validation and SSL
    Steps:
        * Navigate to Containers Menu
        * Navigate to Add Provider Menu
        * Try to add a Container Provider with each of the following security options:
            Default Endpoint = SSL trusting custom CA/SSL without validation/SSL
        * Assert that provider was added successfully
        """
    new_provider = copy(provider)
    new_provider.endpoints['default'].sec_protocol = default_sec_protocol
    try:
        new_provider.setup()
    except FlashMessageException:
        soft_assert(False, provider.name + ' wasn\'t added successfully using ' +
                    default_sec_protocol + ' security protocol')
    ContainersProvider.clear_providers()


@pytest.mark.parametrize('test_item', TEST_ITEMS, ids=[
    'Default: {} /  Hawkular: {}'.format(
        ti.args[1].default_sec_protocol, ti.args[1].hawkular_sec_protocol)
    for ti in TEST_ITEMS])
@pytest.mark.usefixtures('has_no_containers_providers')
def test_add_hawkular_provider_ssl(provider, appliance, test_item, soft_assert):
    """This test checks adding container providers with 3 different security protocols:
    SSL trusting custom CA, SSL without validation and SSL
    The test checks the Default Endpoint as well as the Hawkular Endpoint
    Steps:
        * Navigate to Containers Menu
        * Navigate to Add Provider Menu
        * Try to add a Container Provider with each of the following security options:
            Default Endpoint = SSL trusting custom CA/SSL without validation/SSL
            Hawkular Endpoint = SSL trusting custom CA/SSL without validation/SSL
        * Assert that provider was added successfully
        """
    new_provider = copy(provider)
    new_provider.endpoints['default'].sec_protocol = test_item.default_sec_protocol
    new_provider.endpoints['hawkular'].sec_protocol = test_item.hawkular_sec_protocol
    try:
        new_provider.setup()
        view = appliance.browser.create_view(ContainerProvidersView)
        view.flash.assert_success_message(
            'Containers Providers "' + provider.name + '" was saved')
    except FlashMessageException:
        soft_assert(False, provider.name + ' wasn\'t added successfully using ' +
                    test_item.default_sec_protocol + ' security protocol and ' +
                    test_item.hawkular_sec_protocol + ' hawkular security protocol')
