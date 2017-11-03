
import uuid
import fauxfactory
import pytest
from copy import copy, deepcopy

from cfme.base.credential import Credential
from cfme.common.provider_views import (MiddlewareProviderAddView,
                                    MiddlewareProvidersView,
                                    MiddlewareProviderDetailsView)
from cfme.middleware.provider import MiddlewareProvider
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.utils import error
from cfme.utils import testgen
from cfme.utils.update import update
from cfme.utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < '5.8'),
]
pytest_generate_tests = testgen.generate([MiddlewareProvider], scope='function')


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_add_with_bad_credentials(provider):
    """ Tests provider add with bad credentials"""
    provider.endpoints['default'].credentials = Credential(
        principal='bad',
        secret='reallybad'
    )
    with error.expected('Credential validation was not successful: Invalid credentials'):
        provider.create(validate_credentials=True)
    view = provider.create_view(MiddlewareProviderAddView)
    assert not view.add.active


def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = HawkularProvider()
    prov.create(cancel=True)
    view = prov.browser.create_view(MiddlewareProvidersView)
    view.flash.assert_success_message('Add of Middleware Provider was cancelled by the user')


def test_password_mismatch_validation(provider, soft_assert):
    """ Tests password mismatch check """
    prov = copy(provider)
    endpoints = deepcopy(prov.endpoints)
    endpoints['default'].credentials = Credential(
        principal='bad',
        secret=fauxfactory.gen_alphanumeric(5),
        verify_secret=fauxfactory.gen_alphanumeric(6)
    )
    prov.endpoints = endpoints
    message = 'Credential validation was successful'
    if current_version() >= '5.9':
        message = 'Credential validation was not successful: Invalid credentials'
    with error.expected(message):
        prov.create()
    add_view = provider.create_view(MiddlewareProviderAddView)
    endp_view = prov.endpoints_form(parent=add_view)
    soft_assert(not endp_view.validate.active)
    soft_assert(not add_view.add.active)
    # TODO enable once confirm_password.help_block returns correct text
    # soft_assert(endp_view.confirm_password.help_block == "Passwords do not match")


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:8241'])
@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_add_with_invalid_port(provider, soft_assert):
    """ Tests provider add with bad port (non-numeric)"""
    prov = copy(provider)
    endpoints = deepcopy(prov.endpoints)
    endpoints['default'].api_port = fauxfactory.gen_alpha(6)
    prov.endpoints = endpoints
    with error.expected('Credential validation was successful'):
        prov.create()
    add_view = provider.create_view(MiddlewareProviderAddView)
    endp_view = provider.endpoints_form(parent=add_view)
    soft_assert(not add_view.add.active)
    soft_assert(not endp_view.validate.active)
    soft_assert(endp_view.api_port.help_block ==
                "Must be a number (greater than 0)")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_provider_add_with_bad_port(provider):
    """ Tests provider add with bad port (incorrect)"""
    provider.endpoints['default'].api_port = 8888
    with error.expected('Credential validation was not successful: Unable to connect to {}:8888'
                        .format(provider.hostname)):
        provider.create(validate_credentials=True)


def test_provider_add_with_bad_hostname(provider):
    """ Tests provider add with bad hostname (incorrect)"""
    provider.endpoints['default'].hostname = 'incorrect'
    with error.expected(
            'Credential validation was not successful: Unable to connect to incorrect:{}'
            .format(provider.port)):
        provider.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_required_fields_validation(provider, soft_assert):
    """Test to validate all required fields while adding a provider"""
    prov = copy(provider)
    prov.name = ''
    endpoints = deepcopy(prov.endpoints)
    endpoints['default'].credentials = Credential('', '')
    endpoints['default'].hostname = ''
    prov.endpoints = endpoints
    with error.expected('Credential validation was successful'):
        prov.create()
    add_view = provider.create_view(MiddlewareProviderAddView)
    endp_view = provider.endpoints_form(parent=add_view)
    soft_assert(not add_view.add.active)
    soft_assert(not endp_view.validate.active)
    soft_assert(add_view.name.help_block == "Required")
    soft_assert(endp_view.hostname.help_block == "Required")
    # TODO activate when api_port.help_block return value
    # soft_assert(endp_view.api_port.help_block == "Required")
    soft_assert(endp_view.username.help_block == "Required")
    soft_assert(endp_view.password.help_block == "Required")
    # TODO activate when confirm_password.help_block return value
    # soft_assert(endp_view.confirm_password.help_block == "Required")


@pytest.mark.usefixtures('setup_provider')
def test_duplicite_provider_creation(provider):
    """Tests that creation of already existing provider fails."""
    message = 'Name has already been taken, Host Name has already been taken'
    if current_version() >= '5.8':
        message = 'Name has already been taken'
    with error.expected(message):
        provider.create(cancel=False, validate_credentials=True)
# TODO - this checks only hostname err msgs, we need two providers to check name err msg as well


@pytest.mark.smoke
@pytest.mark.usefixtures('has_no_middleware_providers')
def test_hawkular_crud(provider):
    """Test provider add with good credentials.

    """
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
def test_authentication(provider):
    """Tests executing "Re-check Authentication Status" menu item.
    Verifies that success message is shown.
    """
    provider.recheck_auth_status()
    view = provider.create_view(MiddlewareProviderDetailsView)
    view.flash.assert_success_message('Authentication status will be saved'
        ' and workers will be restarted for the selected Middleware Provider')


@pytest.mark.uncollectif(lambda: current_version() < '5.9')
@pytest.mark.usefixtures('setup_provider')
def test_auth_status(provider):
    """Verifies that Authentication status for provider is: Valid - Ok.
    """
    assert provider.is_valid(), 'Authentication status should be: Valid - Ok'
