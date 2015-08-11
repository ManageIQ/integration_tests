"""``setup_provider`` fixture

In test modules paramatrized with :py:func:`utils.testgen.provider_by_type` (should be
just about any module that needs a provider to run its tests), this fixture will set up
the single provider needed to run that test.

If the provider setup fails, this fixture will record that failure and skip future tests
using the provider.

"""
import pytest

from cfme.cloud.provider import credential_form
from utils import letobj, providers
from utils.log import logger

# failed provider tracking for _setup_provider_fixture
_failed_providers = set()


def _setup_provider(provider):
    global _failed_providers

    def skip(provider, previous_fail=False):
        if previous_fail:
            raise pytest.skip('Provider {} failed to set up previously in another test, '
                              'skipping test'.format(provider.key))
        else:
            raise pytest.skip('Provider {} failed to set up this time, '
                              'skipping test'.format(provider.key))
    # This function is dynamically "fixturized" to setup up a specific provider,
    # optionally skipping the provider setup if that provider has previously failed.
    if provider.key in _failed_providers:
        skip(provider, previous_fail=True)

    try:
        logger.info('Setting up provider: {} - {}'.format(provider.key, provider.name))
        provider.create(validate_credentials=True)
        provider.validate()
    except Exception as ex:
        logger.error('Error setting up provider {} - {}'.format(provider.key, provider.name))
        logger.exception(ex)
        _failed_providers.add(provider.key)
        skip(provider)


@pytest.yield_fixture(scope="module")
def delete_tenanted_provider_after_module(provider, tenanted_provider):
    yield
    if tenanted_provider.exists:
        tenanted_provider.delete(cancel=False)
        tenanted_provider.wait_for_delete()


@pytest.yield_fixture(scope='function')
def setup_provider(provider, tenanted_provider):
    """Function-scoped fixture to set up a provider"""
    if tenanted_provider is None:
        _setup_provider(provider)
        yield
        return
    else:
        if tenanted_provider.exists:
            # If it exists, let's check if it already has the credentials
            pytest.sel.force_navigate("clouds_provider_edit", context={"provider": provider})
            current_user_name = pytest.sel.value(credential_form.default_principal)
            if current_user_name != tenanted_provider.credentials.principal:
                # It does not, so it is something different - just delete it
                tenanted_provider.delete(cancel=False)
                tenanted_provider.wait_for_delete()
        with letobj(
                provider, credentials=tenanted_provider.credentials, name=tenanted_provider.name):
            # Do provider setup as usual
            _setup_provider(provider)
            yield


@pytest.fixture(scope='module')
def setup_provider_modscope(provider):
    """Function-scoped fixture to set up a provider"""
    _setup_provider(provider)


@pytest.fixture(scope='class')
def setup_provider_clsscope(provider):
    """Module-scoped fixture to set up a provider"""
    _setup_provider(provider)


@pytest.fixture
def setup_provider_funcscope(provider, tenanted_provider):
    """Function-scoped fixture to set up a provider

    Note:

        While there are cases where this is useful, provider fixtures should
        be module-scoped the majority of the time.

    """
    _setup_provider(provider)


@pytest.fixture(scope="session")
def any_provider_session():
    providers.clear_providers()  # To make it clean
    providers.setup_a_provider(validate=True, check_existing=True)
