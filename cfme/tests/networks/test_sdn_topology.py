import pytest
import time
from utils import testgen
from random import choice
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.pytest_selenium import is_displayed_text
from cfme.web_ui.topology import Topology
from utils.browser import WithZoom
from utils.wait import wait_for
from cfme.networks.topology import NetworkTopology


pytest_generate_tests = testgen.generate(
    classes=[EC2Provider, OpenStackProvider, AzureProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.tier(1)
def test_sdn_topology_names(provider, appliance):
    ''' Test network topology names
    Recommendation: Run test with maximed browser to be sure everything is visible
    '''
    topology_object = Topology(NetworkTopology)
    for show_names_state in (True, False):
        topology_object.display_names.enable(show_names_state)
        elements = topology_object.elements()
        with WithZoom(-3):  # zoom out to show all objects
            time.sleep(5)
            for elem in elements:
                assert is_displayed_text(elem.name) == show_names_state


def test_topology_search(provider, appliance):
    '''Testing search functionality in Topology view '''
    topology_object = Topology(NetworkTopology)
    topology_object.display_names.enable(True)
    topology_object.reload_elements()

    wait_for(lambda: len(topology_object.elements()) > 0, fail_func=topology_object.reload_elements,
             delay=3, timeout=60.0)
    elements = topology_object.elements()
    if not elements:
        raise Exception('No elements to test topology')
    element_to_search = choice(elements)
    search_term = element_to_search.name[:len(element_to_search.name) / 2]
    topology_object.search_box.text(text=search_term)
    for el in topology_object.elements():
        if search_term in el.name:
            if el.is_hidden:
                raise Exception('Element should be visible. search: "{}", element found: "{}"'
                                .format(search_term, el.name))
        else:
            if not el.is_hidden:
                raise Exception('Element should be hidden. search: "{}", element found: "{}"'
                                .format(search_term, el.name))


def test_topology_toggle_display(provider):
    '''Testing display functionality in Topology view'''
    topology_object = Topology(NetworkTopology)
    for legend_name in topology_object.legends:
        legend = getattr(topology_object, legend_name)
        for state in (True, False):
            legend.set_active(state)
            topology_object.reload_elements()
            for elem in topology_object.elements():
                if elem.type == legend.name.rstrip('s'):
                    if elem.is_hidden == state:
                        vis_terms = {True: 'Visible', False: 'Hidden'}
                        raise Exception(
                            'Element is {} but should be {} since "{}" display is currently {}'
                            .format(
                                vis_terms[not state], vis_terms[state],
                                legend_name, {True: 'on', False: 'off'}[state]
                            )
                        )

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
