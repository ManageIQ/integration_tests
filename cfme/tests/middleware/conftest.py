from __future__ import unicode_literals
import pytest


@pytest.fixture
def single_middleware_provider(has_no_middleware_providers, provider):
    """This fixture is created to assure that only one middleware provider exists.
    The reason to have separate fixture is, that when using several fixtures,
    one to remove existing providers and
    second to create new provider, does not guarantee the order of execution.
    So this fixture depends on 'has_no_middleware_providers' fixture,
    which deleted existing middleware providers,
    and then created the necessary single provider.

    Used in 'test_middleware_deployment.py' and 'test_middleware_server.py' tests.

    """
    provider.create(validate_credentials=True)
    provider.validate()
    return provider
