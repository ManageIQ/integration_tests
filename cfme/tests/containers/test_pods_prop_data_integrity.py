import pytest
from cfme.containers.pod import Pod, list_tbl
from cfme.containers.provider import ContainersProvider
from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-9934')
def test_summary_properties_validation(provider):
    """ This test verifies that the sum of running, waiting and terminated containers
        in the status summary table
        is the same number that appears in the Relationships table containers field
    """
    navigate_to(Pod, 'All')
    ui_pods = [r.name.text for r in list_tbl.rows()]

    for name in ui_pods:
        obj = Pod(name, provider)
        num_cont_running = obj.summary.container_statuses_summary.running.value
        num_cont_waiting = obj.summary.container_statuses_summary.waiting.value
        num_cont_terminated = obj.summary.container_statuses_summary.terminated.value
        num_cont_total = obj.summary.relationships.containers.value
        assert num_cont_total == num_cont_running + \
            num_cont_terminated + num_cont_waiting
