import pytest
from utils import testgen


pytestmark = [pytest.mark.usefixtures('has_no_container_providers')]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# CMP-9844

def test_provider_valid_token(provider):
    """ Add a provider with the valid token, verify that the
    provider has been  added and the fields have been populated .
    Delete the  provider
    """
    provider.create()
    provider.validate_stats(ui=True)
    provider.delete(cancel=False)
    provider.wait_for_delete()
