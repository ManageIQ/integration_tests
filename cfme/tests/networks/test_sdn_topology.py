import pytest
import time

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.pytest_selenium import is_displayed_text
from cfme.networks.topology import Topology
from cfme.utils import testgen
from cfme.utils.wait import wait_for
from random import choice


pytest_generate_tests = testgen.generate(
    classes=[EC2Provider, AzureProvider, OpenStackProvider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


@pytest.mark.tier(1)
def test_sdn_topology_names(provider, appliance):
    ''' Test network topology names
    Recommendation: Run test with maximed browser to be sure everything is visible
    '''
    topology_object = Topology(appliance)

    for show_names_state in (True, False):
        topology_object.display_names.enable(show_names_state)
        time.sleep(5)
        for elem in topology_object.elements:
            assert is_displayed_text(elem.name) == show_names_state


def test_topology_search(provider, appliance):
    '''Testing search functionality in Topology view '''
    topology_object = Topology(appliance)
    topology_object.display_names.enable(True)

    wait_for(lambda: len(topology_object.elements) > 0,
             fail_func=topology_object.reload_elements_and_lines, delay=3, timeout=60.0)
    elements = topology_object.elements
    if not elements:
        raise Exception('No elements to test topology')
    element_to_search = choice(elements)
    search_term = element_to_search.name[:len(element_to_search.name) / 2]
    topology_object.view.toolbar.search_box.search(text=search_term)

    for element in topology_object.elements:
        if search_term in element.name:
            if element.is_hidden:
                raise Exception('Element should be visible. search: "{}", element found: "{}"'
                                .format(search_term, element.name))
        else:
            if not element.is_hidden:
                raise Exception('Element should be hidden. search: "{}", element found: "{}"'
                                .format(search_term, element.name))

    topology_object.view.toolbar.search_box.clear_search()


def test_topology_toggle_display(provider, appliance):
    '''Testing display functionality in Topology view'''
    topology_object = Topology(appliance)
    for legend in topology_object.legends_obj:
        for state in (True, False):
            legend.set_active(state)
            topology_object.reload_elements_and_lines()
            for elem in topology_object.elements:
                if elem.type == legend.name.rstrip('s'):
                    if elem.is_hidden == state:
                        vis_terms = {True: 'Visible', False: 'Hidden'}
                        raise Exception(
                            'Element is {} but should be {} since "{}" display is currently {}'
                            .format(
                                vis_terms[not state], vis_terms[state],
                                legend.name, {True: 'on', False: 'off'}[state]
                            )
                        )
    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
