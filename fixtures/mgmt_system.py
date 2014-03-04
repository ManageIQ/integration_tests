    # pylint: disable=E1101
import pytest

from utils.providers import (
    clear_providers,
    provider_factory
)
from utils import providers


@pytest.fixture
def setup_providers(uses_providers):
    """Adds all providers listed in cfme_data.yaml

    This includes both cloud and infra provider types.
    """
    providers.setup_providers(validate=True, check_existing=True)


@pytest.fixture
def setup_infrastructure_providers(uses_infra_providers):
    """Adds all infrastructure providers listed in cfme_data.yaml

    This includes ``rhev`` and ``virtualcenter`` provider types
    """
    providers.setup_infrastructure_providers(validate=True, check_existing=True)


@pytest.fixture
def setup_cloud_providers(uses_cloud_providers):
    """Adds all cloud providers listed in cfme_data.yaml

    This includes ``ec2`` and ``openstack`` providers types
    """
    providers.setup_cloud_providers(validate=True, check_existing=True)


@pytest.fixture(scope='module')  # IGNORE:E1101
def mgmt_sys_api_clients(cfme_data, uses_providers):
    """Returns a list of management system api clients"""
    clients = {}
    for provider_key in cfme_data['management_systems']:
        clients[provider_key] = provider_factory(provider_key)
    return clients


@pytest.fixture
def has_no_providers():
    """ Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    """
    clear_providers()
