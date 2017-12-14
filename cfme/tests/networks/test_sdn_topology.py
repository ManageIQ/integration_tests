import pytest
from random import choice

from cfme.cloud.provider.ec2 import EC2Provider
from cfme.networks.topology import TopologyCollection
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytest_generate_tests = testgen.generate(classes=[EC2Provider], scope='module')
pytestmark = pytest.mark.usefixtures('setup_provider')


def test_topology_search(provider, appliance):
    """Testing search functionality in Topology view """
    top_collection = TopologyCollection(appliance)
    topology_object = top_collection.instantiate()
    view = navigate_to(topology_object, 'All')
    topology_object.display_names.enable()

    elements = topology_object.elements
    assert elements, 'No elements to test topology'

    element_to_search = choice(elements)
    search_term = element_to_search.name[:len(element_to_search.name) / 2]
    view.toolbar.search_box.search(text=search_term)

    for element in topology_object.elements:
        if search_term in element.name:
            assert not element.is_hidden, 'Element should be visible.\
                                           search: "{}", found: "{}"'.format(search_term,
                                                                             element.name)
        else:
            assert element.is_hidden, 'Element should not be visible.\
                                       search: "{}", found: "{}"'.format(search_term, element.name)

    view.toolbar.search_box.clear_search()


def test_topology_toggle_display(provider, appliance):
    """Testing display functionality in Topology view"""
    top_collection = TopologyCollection(appliance)
    topology_object = top_collection.instantiate()
    navigate_to(topology_object, 'All')
    for legend in topology_object.legends:
        for state in (True, False):
            legend.set_active(state)
            for elem in topology_object.elements:
                vis_terms = {True: 'Visible', False: 'Hidden'}
                assert elem.type != legend.name.rstrip('s') or elem.is_hidden != state, \
                    'Element is {} but should be {} since "{}" \
                     display is currently {}'.format(vis_terms[not state],
                                                     vis_terms[state],
                                                     legend.name,
                                                     {True: 'on', False: 'off'}[state])

    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()
