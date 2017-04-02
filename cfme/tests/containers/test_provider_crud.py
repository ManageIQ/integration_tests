import uuid
import pytest
from utils import testgen
from utils.providers import setup_a_provider as _setup_a_provider
from utils.update import update
from utils.version import current_version

pytestmark = pytest.mark.uncollectif(lambda: current_version() < "5.6")

pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP -9844 # CMP - 9846


@pytest.yield_fixture(scope="function")
def a_container_provider():
    prov = _setup_a_provider("container")
    yield prov
    prov.delete_if_exists(cancel=False)


@pytest.mark.tier(2)
@pytest.mark.usefixtures('has_no_container_providers')
def test_provider_crud(request, provider):
    """ Adding the provider with valid credentials
    and verifying the fields in the summary page.
    Adding the provider with invalid name and verifying
    that the invalid name is not accepted

    Metadata:
        test_flag: crud
    """
    provider.create()
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()
