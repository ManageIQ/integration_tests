from collections import namedtuple
from copy import copy

import pytest
from fauxfactory import gen_alphanumeric
from fauxfactory import gen_integer

from cfme import test_requirements
from cfme.common.provider_views import ContainerProvidersView
from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.provider([ContainersProvider], scope='module'),
    test_requirements.containers
]

alphanumeric_name = gen_alphanumeric(10)
long_alphanumeric_name = gen_alphanumeric(100)
integer_name = str(gen_integer(0, 100000000))
provider_names = alphanumeric_name, integer_name, long_alphanumeric_name
AVAILABLE_SEC_PROTOCOLS = ('SSL trusting custom CA', 'SSL without validation', 'SSL')

DEFAULT_SEC_PROTOCOLS = ('SSL trusting custom CA', 'SSL without validation', 'SSL')

checked_item = namedtuple('TestItem', ['default_sec_protocol', 'metrics_sec_protocol'])

TEST_ITEMS = (
    checked_item('SSL trusting custom CA', 'SSL trusting custom CA'),
    checked_item('SSL trusting custom CA', 'SSL without validation'),
    checked_item('SSL trusting custom CA', 'SSL'),
    checked_item('SSL without validation', 'SSL trusting custom CA'),
    checked_item('SSL without validation', 'SSL without validation'),
    checked_item('SSL without validation', 'SSL'),
    checked_item('SSL', 'SSL trusting custom CA'),
    checked_item('SSL', 'SSL without validation'),
    checked_item('SSL', 'SSL'))


@pytest.fixture(scope="module")
def sync_ssl_certificate(provider):
    provider.sync_ssl_certificate()


@pytest.mark.usefixtures('has_no_containers_providers')
def test_add_provider_naming_conventions(provider, appliance, soft_assert, sync_ssl_certificate):
    """" This test is checking ability to add Providers with different names:

    Steps:
        * Navigate to Containers Menu
        * Navigate to Add Provider Menu
        * Try to add a Container Provider with each of the following generated names:
            - Alphanumeric name
            - Long Alphanumeric name
            - Integer name
        * Assert that provider was added successfully with each of those

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
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
        except AssertionError:
            soft_assert(False, provider_name + ' wasn\'t added successfully')
        else:
            new_provider.delete()
            new_provider.wait_for_delete()


@pytest.mark.parametrize('default_sec_protocol', DEFAULT_SEC_PROTOCOLS)
@pytest.mark.usefixtures('has_no_containers_providers')
def test_add_provider_ssl(provider, default_sec_protocol, soft_assert, sync_ssl_certificate):
    """ This test checks adding container providers with 3 different security protocols:
    SSL trusting custom CA, SSL without validation and SSL
    Steps:
        * Navigate to Containers Menu
        * Navigate to Add Provider Menu
        * Try to add a Container Provider with each of the following security options:
            Default Endpoint = SSL trusting custom CA/SSL without validation/SSL
        * Assert that provider was added successfully

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    new_provider = copy(provider)
    endpoints = {'default': new_provider.endpoints['default']}
    endpoints['default'].sec_protocol = default_sec_protocol

    new_provider.endpoints = endpoints
    new_provider.metrics_type = 'Disabled'
    new_provider.alerts_type = 'Disabled'
    try:
        new_provider.setup()
    except AssertionError:
        soft_assert(False, provider.name + ' wasn\'t added successfully using ' +
                    default_sec_protocol + ' security protocol')
    else:
        new_provider.delete()
        new_provider.wait_for_delete()


@pytest.mark.parametrize('test_item', TEST_ITEMS, ids=[
    'Default: {} /  Metrics: {}'.format(
        ti.default_sec_protocol, ti.metrics_sec_protocol)
    for ti in TEST_ITEMS])
@pytest.mark.usefixtures('has_no_containers_providers')
def test_add_mertics_provider_ssl(provider, appliance, test_item,
                                  soft_assert, sync_ssl_certificate):
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

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    if not provider.endpoints.get('metrics', False):
        pytest.skip("This test requires the metrics endpoint to be configured")
    new_provider = copy(provider)
    new_provider.endpoints['default'].sec_protocol = test_item.default_sec_protocol
    new_provider.endpoints['metrics'].sec_protocol = test_item.metrics_sec_protocol

    try:
        new_provider.setup()
        view = appliance.browser.create_view(ContainerProvidersView)
        view.flash.assert_success_message(
            'Containers Providers "' + provider.name + '" was saved')
    except AssertionError:
        soft_assert(False,
                    ("{provider_name} wasn't added successfully using {default_sec_protocol} "
                     "security protocol and {metrics_sec_protocol} "
                     "metrics security protocol").format(
                        provider_name=provider.name,
                        default_sec_protocol=test_item.default_sec_protocol,
                        metrics_sec_protocol=test_item.metrics_sec_protocol))
    else:
        new_provider.delete()
        new_provider.wait_for_delete()


@pytest.mark.usefixtures('has_no_containers_providers')
@pytest.mark.parametrize('sec_protocol', AVAILABLE_SEC_PROTOCOLS)
def test_setup_with_wrong_port(provider, sec_protocol, sync_ssl_certificate):
    """
    Negative test: set a provider with wrong api port
    based on BZ1443520

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    new_provider = copy(provider)
    new_provider.endpoints["default"].api_port = "1234"
    new_provider.endpoints["default"].sec_protocol = sec_protocol

    with pytest.raises(AssertionError, message="Provider was set with wrong api port"):
        new_provider.setup()
