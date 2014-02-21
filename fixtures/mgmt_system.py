    # pylint: disable=E1101
import logging

import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import paginator, Quadicon
from utils.conf import cfme_data
from utils.providers import (
    infra_provider_type_map,
    cloud_provider_type_map,
    provider_factory
)
from utils import providers

logger = logging.getLogger(__name__)


@pytest.fixture
def setup_infrastructure_providers():
    """Adds all infrastructure providers listed in cfme_data.yaml

    This includes ``rhev`` and ``virtualcenter`` provider types
    """
    sel.force_navigate('infrastructure_providers')
    # Does provider exist
    providers_to_add = []
    for provider, prov_data in cfme_data['management_systems'].iteritems():
        if prov_data['type'] not in infra_provider_type_map:
            # short out if we don't care about this provider type
            continue

        quad = Quadicon(prov_data['name'], 'infra_prov')
        for page in paginator.pages():
            if sel.is_displayed(quad):
                break
        else:
            providers_to_add.append(provider)

    for provider in providers_to_add:
        providers.setup_infrastructure_provider(provider, validate=True)


@pytest.fixture
def setup_cloud_providers():
    """Adds all cloud providers listed in cfme_data.yaml

    This includes ``ec2`` and ``openstack`` providers types
    """
    # Does provider exist
    sel.force_navigate('clouds_providers')
    # Does provider exist
    providers_to_add = []
    for provider, prov_data in cfme_data['management_systems'].iteritems():
        if prov_data['type'] not in cloud_provider_type_map:
            # short out if we don't care about this provider type
            continue

        quad = Quadicon(prov_data['name'], 'cloud_prov')
        for page in paginator.pages():
            if sel.is_displayed(quad):
                break
        else:
            providers_to_add.append(provider)

    for provider in providers_to_add:
        providers.setup_cloud_provider(provider, validate=True)


@pytest.fixture(scope='module')  # IGNORE:E1101
def mgmt_sys_api_clients(cfme_data):
    """Returns a list of management system api clients"""
    clients = {}
    for sys_name in cfme_data['management_systems']:
        if sys_name in clients:
            # Overlapping sys_name entry in cfme_data.yaml
            logger.warning('Overriding existing entry for %s.' % sys_name)
        clients[sys_name] = provider_factory(sys_name)
    return clients
