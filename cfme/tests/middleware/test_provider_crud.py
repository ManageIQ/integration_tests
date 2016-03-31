import pytest
from cfme import login
from utils import providers

login.login_admin()


<<<<<<< HEAD
@pytest.fixture(scope='function')
def hawkular_provider():
    return providers.get_crud('hawkular')


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_hawkular_crud(hawkular_provider):
    """Test provider add with good credentials.

    has_no_middleware_providers fixture is not yet implemented.  You must manually remove
    added providers between test runs
    """
    hawkular_provider.create(cancel=False, validate_credentials=False)
=======
hawkular.create(cancel=False, validate_credentials=False)
>>>>>>> W292
