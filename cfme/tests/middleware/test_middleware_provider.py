import fauxfactory
import uuid

import pytest

import utils.error as error
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.web_ui import fill, flash, form_buttons
from cfme.fixtures import pytest_selenium as sel
from cfme.exceptions import FlashMessageException
from utils import testgen
from utils.update import update
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]

pytest_generate_tests = testgen.generate(testgen.middleware_providers, scope="function")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_add_with_bad_credentials(provider):
    """ Tests provider add with bad credentials"""
    provider.credentials['default'] = provider.Credential(
        principal='bad',
        secret='reallybad'
    )
    with error.expected('Credential validation was not successful: Invalid credentials'):
        provider.create(validate_credentials=True)
    assert (not provider.add_provider_button.can_be_clicked)


def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = HawkularProvider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of Middleware Provider was cancelled by the user')


def test_password_mismatch_validation(soft_assert):
    """ Tests password mismatch check """
    prov = HawkularProvider()
    cred = prov.Credential(
        principal='bad',
        secret=fauxfactory.gen_alphanumeric(5),
        verify_secret=fauxfactory.gen_alphanumeric(6)
    )
    navigate_to(prov, 'Add')
    fill(prov.properties_form, {"type_select": "Hawkular", "hostname_text": "test",
                                "name_text": "test", "port_text": "8080"})
    fill(cred.form, cred)
    sel.wait_for_ajax()
    soft_assert(not form_buttons.validate.can_be_clicked)
    soft_assert(not prov.add_provider_button.can_be_clicked)
    soft_assert(cred.form.default_verify_secret.angular_help_block == "Passwords do not match")


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:8241'])
@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_add_with_invalid_port(provider, soft_assert):
    """ Tests provider add with bad port (non-numeric)"""
    provider.port = fauxfactory.gen_alpha(6)
    with error.expected(FlashMessageException):
            provider.create(validate_credentials=False)
    soft_assert(not provider.add_provider_button.can_be_clicked)
    soft_assert(provider.properties_form.port_text.angular_help_block ==
                "Must be a number (greater than 0)")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_add_with_bad_port(provider):
    """ Tests provider add with bad port (incorrect)"""
    provider.port = 8888
    with error.expected('Credential validation was not successful: Unable to connect to {}:8888'
                        .format(provider.hostname)):
        with sel.ajax_timeout(120):
            provider.create(validate_credentials=True)


def test_provider_add_with_bad_hostname(provider):
    """ Tests provider add with bad hostname (incorrect)"""
    provider.hostname = 'incorrect'
    with error.expected(
            'Credential validation was not successful: Unable to connect to incorrect:{}'
            .format(provider.port)):
        with sel.ajax_timeout(120):
            provider.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_required_fields_validation(provider, soft_assert):
    """Test to validate all required fields while adding a provider"""
    navigate_to(provider, 'Add')
    cred = provider.Credential()
    fill(provider.properties_form, {"type_select": "Hawkular"})
    soft_assert(not provider.add_provider_button.can_be_clicked)
    soft_assert(not form_buttons.validate.can_be_clicked)
    soft_assert(provider.properties_form.name_text.angular_help_block == "Required")
    soft_assert(provider.properties_form.hostname_text.angular_help_block == "Required")
    soft_assert(provider.properties_form.port_text.angular_help_block == "Required")
    soft_assert(cred.form.default_principal.angular_help_block == "Required")
    soft_assert(cred.form.default_secret.angular_help_block == "Required")
    soft_assert(cred.form.default_verify_secret.angular_help_block == "Required")


@pytest.mark.usefixtures('setup_provider')
def test_duplicite_provider_creation(provider):
    """Tests that creation of already existing provider fails."""
    with error.expected('Host Name has already been taken'):
        provider.create(cancel=False, validate_credentials=True)
# TODO - this checks only hostname err msgs, we need two providers to check name err msg as well


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_hawkular_crud(provider):
    """Test provider add with good credentials.

    """
    with sel.ajax_timeout(120):
        provider.create(cancel=False, validate_credentials=True)
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
        * Check number of `Servers`, `Domains`, `Messagings`,
        * `Datasources`, `Server Groups`, `Deployments` on topology page
    """

    # reload topology page to make sure all elements are loaded
    provider.topology.reload()

    assert len(provider.topology.elements(element_type='Hawkular')) == 1,\
        "More than one Hawkular providers found"

    assert provider.num_server(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareServer')), \
        "Number of server(s) miss match between topology page and in database"

    assert provider.num_messaging(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareMessaging')), \
        "Number of messaging(s) miss match between topology page and in database"

    assert provider.num_datasource(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareDatasource')), \
        "Number of datasource(s) miss match between topology page and in database"

    assert provider.num_domain(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareDomain')), \
        "Number of domain(s) miss match between topology page and in database"

    assert provider.num_server_group(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareServerGroup')), \
        "Number of server_group(s) miss match between topology page and in database"

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
        ' and workers will be restarted for the selected Middleware Provider')
