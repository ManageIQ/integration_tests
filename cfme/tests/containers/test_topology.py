# import time
# from random import choice
import pytest

from cfme.containers.provider import ContainersProvider
# from cfme.utils.blockers import BZ
# from cfme.utils.wait import wait_for
# from cfme.utils.browser import WithZoom
# from cfme.containers.topology import Topology as ContainerTopology
# from cfme.fixtures.pytest_selenium import is_displayed_text


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


# Remove until Topology has been replaced
# @pytest.mark.polarion('CMP-9996')
# def test_topology_display_names():
#     """Testing Display Names functionality in Topology view/
#
#     Steps:
#         * In Topology screen click on the Display names check box.
#
#     Expected result:
#         The entities names should toggle on/off according to the state of the checkbox.
#     """
#     topo_obj = Topology(ContainerTopology)
#     for bool_ in (True, False):
#         topo_obj.display_names.enable(bool_)
#         elements = topo_obj.elements()
#         # The extreme zoom is in order to include all the view
#         # in the screen and don't miss any item
#         with WithZoom(-10):
#             time.sleep(5)
#             for elem in elements:
#                 assert is_displayed_text(elem.name) == bool_
#
#
# @pytest.mark.meta(blockers=[BZ(1467064, forced_streams=['5.8'])])
# @pytest.mark.polarion('CMP-9998')
# def test_topology_search():
#     """Testing search functionality in Topology view.
#
#     Steps:
#         * In Search text box enter valid name of an entity.
#
#     Expected result:
#         Entity found, should be highlighted and all other entities should be "disabled"
#     """
#     topo_obj = Topology(ContainerTopology)
#     topo_obj.display_names.enable(True)  # For better debugging on failures
#     topo_obj.reload_elements()  # we reload again to prevent stale element exception
#     wait_for(lambda: len(topo_obj.elements()) > 0, fail_func=topo_obj.reload_elements,
#              delay=3, timeout=60.0)
#     elements = topo_obj.elements()
#     if not elements:
#         raise Exception('No elements to test topology')
#     element_to_search = choice(elements)
#     search_term = element_to_search.name[:len(element_to_search.name) / 2]
#     topo_obj.search_box.text(text=search_term)
#     for el in topo_obj.elements():
#         if search_term in el.name:
#             if el.is_hidden:
#                 raise Exception('Element should be visible. search: "{}", element found: "{}"'
#                                 .format(search_term, el.name))
#         else:
#             if not el.is_hidden:
#                 raise Exception('Element should be hidden. search: "{}", element found: "{}"'
#                                 .format(search_term, el.name))
#
#
# @pytest.mark.polarion('CMP-9999')
# def test_topology_toggle_display():
#     """Testing display functionality in Topology view.
#
#     Steps:
#         * For each legend click "enable/disable".
#
#     Expected result:
#         Entities within the Topology map should be hidden/shown as per selection.
#     """
#     topo_obj = Topology(ContainerTopology)
#     for legend_name in topo_obj.legends:
#         legend = getattr(topo_obj, legend_name)
#         for bool_ in (True, False):
#             legend.set_active(bool_)
#             topo_obj.reload_elements()
#             for elem in topo_obj.elements():
#                 # legend.name.rstrip('s') because the 's' in the end, which is redundant
#                 if elem.type == legend.name.rstrip('s'):
#                     if elem.is_hidden == bool_:
#                         vis_terms = {True: 'Visible', False: 'Hidden'}
#                         raise Exception(
#                             'Element is {} but should be {} since "{}" display is currently {}'
#                             .format(
#                                 vis_terms[not bool_], vis_terms[bool_],
#                                 legend_name, {True: 'on', False: 'off'}[bool_]
#                             )
#                         )
