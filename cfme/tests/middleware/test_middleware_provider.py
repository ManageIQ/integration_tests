from __future__ import unicode_literals
import uuid

import pytest
from cfme.web_ui import flash
from utils import testgen
from utils.update import update
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.middleware_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_hawkular_crud(provider):
    """Test provider add with good credentials.

    """
    provider.create(cancel=False, validate_credentials=False)
    # UI validation, checks whether data provided from Hawkular provider matches data in UI
    provider.validate_stats(ui=True)
    # DB validation, checks whether data provided from Hawkular provider matches data in DB
    provider.validate_stats()
    # validates Properties section of provider's summary page
    provider.validate_properties()
    # validates that provider is refreshed in DB and in UI
    assert provider.is_refreshed(method='ui'), "Provider is not refreshed in UI"
    assert provider.is_refreshed(method='db'), "Provider is not refreshed in DB"

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()


@pytest.mark.usefixtures('setup_provider')
def test_topology(provider):
    """Tests topology page from provider page

    Steps:
        * Get topology elements detail
        * Check number of providers on the page
        * Check number of `Servers`, `Deployments` on topology page
    """
    assert len(provider.topology.elements(element_type='Hawkular')) == 1,\
        "More than one Hawkular providers found"
    el_hawkular = provider.topology.elements(element_type='Hawkular')[0]
    assert provider.num_server(method='db') == len(el_hawkular.children), \
        "Number of server(s) miss match between topology page and in database"
    assert provider.num_deployment(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareDeployment')) + \
        len(provider.topology.elements(element_type='MiddlewareDeploymentWar')) + \
        len(provider.topology.elements(element_type='MiddlewareDeploymentEar')),\
        "Number of deployment(s) miss match between topology page and in database"


@pytest.mark.usefixtures('setup_provider')
def test_authentication(provider):
    """Tests executing "Re-check Authentication Status" menu item.
    Verifies that success message is shown.
    """
    provider.recheck_auth_status()
    flash.assert_success_message('Authentication status will be saved'
        ' and workers will be restarted for this Middleware Provider')
