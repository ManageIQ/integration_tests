import pytest
from utils import testgen
from cfme.containers.provider import ContainersProvider
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.8"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.fixture(scope="function")
def validate_logging_up_and_running(provider):
    routers = [router for router in provider.mgmt.o_api.get('route')[1]['items']
               if "logging" in router["metadata"]["name"]]
    all_routers_up = all([router["status"]["ingress"][0]["conditions"][0]["status"]
                          for router in routers])

    assert len(routers) <= 2, "some logging route is missing"
    assert all_routers_up, "some logging route is off"


@pytest.mark.polarion('CMP-10643')
def test_external_logging_activated(provider, validate_logging_up_and_running):
    view = navigate_to(provider, 'Details')

    assert not view.monitor.item_enabled('External Logging'), (
        "Monitoring --> External Logging not activated")

    view.monitor.item_select('External Logging')
