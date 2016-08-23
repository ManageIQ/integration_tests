import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox
from utils import testgen
from utils.version import current_version
import time

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


# container_dashboard
# CMP-9822
def test_containers_summary_containers(provider):
    """ Containers overview page > Containers widget > Containers summary
       This test checks that the amount of containers in the system is shown correctly
        in the Containers widget in the
       Overview menu
       Steps:
           * Goes to Compute --> Containers --> Overview
           * Checks how many Containers are shown in the Containers Widget
           * Goes to Containers summary page and checks how many Containers are shown there.
           * Checks the amount is equal
       """
    sel.force_navigate('container_dashboard')
    time.sleep(2)
    containers_amount = StatusBox('containers').value()
    sel.force_navigate('containers_provider', context={'provider': provider})
    cont_val = provider.summary.relationships.containers.value
    assert cont_val == containers_amount


# CMP-9821
def test_containers_summary_pods(provider):
    """ Containers overview page > Pods widget > Pods summary
        This test checks that the amount of containers in the system is shown correctly
         in the Pods widget in the
        Overview menu
        Steps:
            * Goes to Compute --> Containers --> Overview
            * Checks how many Pods are shown in the Pods Widget
            * Goes to Pods summary page and checks how many Pods are shown there.
            * Checks the amount is equal
        """
    sel.force_navigate('container_dashboard')
    time.sleep(2)
    pods_amount = StatusBox('pods').value()
    sel.force_navigate('containers_provider', context={'provider': provider})
    cont_val = provider.summary.relationships.pods.value
    assert cont_val == pods_amount


# CMP-9820
def test_containers_summary_nodes(provider):
    """ Containers overview page > Containers widget > Nodes summary
        This test checks that the amount of containers in the system is shown correctly
        in the Nodes widget in the
        Overview menu
        Steps:
            * Goes to Compute --> Containers --> Overview
            * Checks how many Nodes are shown in the Nodes Widget
            * Goes to Nodes summary page and checks how many Nodes are shown there.
            * Checks the amount is equal
        """
    sel.force_navigate('container_dashboard')
    time.sleep(2)
    nodes_amount = StatusBox('nodes').value()
    sel.force_navigate('containers_provider', context={'provider': provider})
    cont_val = provider.summary.relationships.nodes.value
    assert cont_val == nodes_amount
