import uuid
import pytest
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
