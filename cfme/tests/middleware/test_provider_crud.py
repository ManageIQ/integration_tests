import pytest
from utils import testgen


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.middleware_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_hawkular_crud(provider):
    """Test provider add with good credentials.

    has_no_middleware_providers fixture is not yet implemented.  You must manually remove
    added providers between test runs
    """
    provider.create(cancel=False, validate_credentials=False)
