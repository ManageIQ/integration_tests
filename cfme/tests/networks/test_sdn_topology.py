import pytest
from random import choice

from cfme.cloud.provider.ec2 import EC2Provider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([EC2Provider], scope='module')
]


def test_topology_search(provider, appliance):
    """Testing search functionality in Topology view """
    elements_collection = appliance.collections.network_topology_elements
    elements = elements_collection.all()
    assert elements_collection.all(), 'No elements to test topology'
    element_to_search = choice(elements)
    search_term = element_to_search.name[:len(element_to_search.name) / 2]
    elements_collection.search(search_term)
    for element in elements:
        if search_term in element.name:
            assert not element.is_opaqued, 'Element should be not opaqued.\
                                            search: "{}", found: "{}"'.format(search_term,
                                                                              element.name)
        else:
            assert element.is_opaqued, 'Element should be opaqued.\
                                        search: "{}", found: "{}"'.format(search_term, element.name)
    view = navigate_to(elements_collection, 'All')
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
