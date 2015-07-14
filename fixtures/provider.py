"""``setup_provider`` fixture

In test modules paramatrized with :py:func:`utils.testgen.provider_by_type` (should be
just about any module that needs a provider to run its tests), this fixture will set up
the single provider needed to run that test.

If the provider setup fails, this fixture will record that failure and skip future tests
using the provider.

"""
import pytest

from utils import providers
from utils.log import logger

# failed provider tracking for _setup_provider_fixture
_failed_providers = set()


def _setup_provider(provider_key):
    def skip(provider_key, previous_fail=False):
        if previous_fail:
            raise pytest.skip('Provider {} failed to set up previously in another test, '
                              'skipping test'.format(provider_key))
        else:
            raise pytest.skip('Provider {} failed to set up this time, '
                              'skipping test'.format(provider_key))
    # This function is dynamically "fixturized" to setup up a specific provider,
    # optionally skipping the provider setup if that provider has previously failed.
    if provider_key in _failed_providers:
        skip(provider_key, previous_fail=True)

    try:
        providers.setup_provider(provider_key)
    except Exception as ex:
        logger.error('Error setting up provider %s', provider_key)
        logger.exception(ex)
        _failed_providers.add(provider_key)
        skip(provider_key)


@pytest.fixture(scope='module')
def setup_provider(provider_key):
    """Module-scoped fixture to set up a provider"""
    _setup_provider(provider_key)


@pytest.fixture(scope='class')
def setup_provider_clsscope(provider_key):
    """Module-scoped fixture to set up a provider"""
    _setup_provider(provider_key)


@pytest.fixture
def setup_provider_funcscope(provider_key):
    """Function-scoped fixture to set up a provider

    Note:

        While there are cases where this is useful, provider fixtures should
        be module-scoped the majority of the time.

    """
    _setup_provider(provider_key)


@pytest.fixture(scope="session")
def any_provider_session():
    providers.clear_providers()  # To make it clean
    providers.setup_a_provider(validate=True, check_existing=True)
