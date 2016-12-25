import pytest

from utils import testgen
from utils.providers import setup_a_provider as _setup_a_provider


pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# 9844


@pytest.fixture(scope="function")
def a_container_provider():
    return _setup_a_provider("container")


def test_provider_valid_token(provider):
    """ Add a provider with the valid token, verify that the
          provider has been  added and the fields have been populated .
          Delete the  provider

    """
    provider.create()
    provider.validate_stats(ui=True)
    provider.delete(cancel=False)
    provider.wait_for_delete()
