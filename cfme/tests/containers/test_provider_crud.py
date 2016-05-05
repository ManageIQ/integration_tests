import uuid
import pytest

from utils import testgen
from utils.providers import setup_a_provider as _setup_a_provider
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.container_providers, scope="function")


@pytest.yield_fixture(scope="function")
def a_container_provider():
    prov = _setup_a_provider("container")
    yield prov
    prov.delete_if_exists(cancel=False)


@pytest.mark.usefixtures('has_no_container_providers')
def test_provider_crud(request, provider):
    """ Tests provider add with good credentials

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


@pytest.mark.meta(blockers=[1274842])
def test_provider_edit_port(request, a_container_provider):
    old_port = a_container_provider.port
    request.addfinalizer(lambda: a_container_provider.update({'port': old_port}))
    with update(a_container_provider):
        a_container_provider.port = '1234'
    assert str(a_container_provider.port) == a_container_provider.get_detail('Properties', 'Port')
