import pytest

from cfme.common.provider import BaseProvider
from utils import providers


@pytest.fixture(scope='module')  # IGNORE:E1101
def mgmt_sys_api_clients(cfme_data, uses_providers):
    """Returns a list of management system api clients"""
    clients = {}
    for provider_key in cfme_data['management_systems']:
        clients[provider_key] = providers.get_mgmt(provider_key)
    return clients


@pytest.fixture
def has_no_providers():
    """ Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers()


@pytest.fixture
def has_no_cloud_providers():
    """ Clears all cloud providers from an appliance

    This is a destructive fixture. It will clear all cloud managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers_by_class(BaseProvider.base_types['cloud'], validate=True)


@pytest.fixture
def has_no_infra_providers():
    """ Clears all infrastructure providers from an appliance

    This is a destructive fixture. It will clear all infrastructure managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers_by_class(BaseProvider.base_types['infra'], validate=True)


@pytest.fixture
def has_no_containers_providers():
    """ Clears all containers providers from an appliance

    This is a destructive fixture. It will clear all container managements systems from
    the current appliance.
    """
    BaseProvider.clear_providers_by_class(BaseProvider.base_types['container'], validate=True)


@pytest.fixture
def has_no_middleware_providers():
    """Clear all middleware providers."""
    BaseProvider.clear_providers_by_class(BaseProvider.base_types['middleware'], validate=True)
