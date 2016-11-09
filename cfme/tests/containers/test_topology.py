# -*- coding: utf-8 -*-
import pytest
from utils import testgen
from utils.version import current_version
from cfme.web_ui.topology import Topology
from cfme.containers.topology import Topology as ContainerTopology
from cfme.fixtures.pytest_selenium import is_displayed_text
from random import choice

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9996


def test_topology_display_names():
    """Testing Display Names functionality in Topology view/

    Steps:
        * In Topology screen click on the Display names check box.

    Expected result:
        The entities names should toggle on/off according to the state of the checkbox.
    """
    topo_obj = Topology(ContainerTopology)

    for bool_ in (True, False):
        topo_obj.display_names.enable(bool_)
        elements = topo_obj.elements()
        for elem in elements:
            assert is_displayed_text(elem.name) == bool_


# CMP-9998


def test_topology_search():
    """Testing search functionality in Topology view.

    Steps:
        * In Search text box enter valid name of an entity.

    Expected result:
        Entity found, should be highlighted and all other entities should be "disabled"
    """
    topo_obj = Topology(ContainerTopology)
    elements = topo_obj.elements()
    if not elements:
        raise Exception('No elements to test topology')
    element_to_search = elements[choice(range(len(elements)))]
    topo_obj.reload_elements()  # we reload again to prevent stale element exception
    topo_obj.search_box.text(text=element_to_search.name)
    for el in topo_obj.elements():
        if element_to_search.name in el.name:
            assert not el.is_hidden
        else:
            assert el.is_hidden

# CMP-9999


def test_topology_toggle_display():
    """Testing display functionality in Topology view.

    Steps:
        * For each legend click "enable/disable".

    Expected result:
        Entities within the Topology map should be hidden/shown as per selection.
    """
    topo_obj = Topology(ContainerTopology)
    for legend_name in topo_obj.legends:
        legend = getattr(topo_obj, legend_name)
        for bool_ in (True, False):
            legend.set_active(bool_)
            topo_obj.reload_elements()
            for elem in topo_obj.elements():
                # legend.name.rstrip('s') because the 's' in the end, which is redundant
                if elem.type == legend.name.rstrip('s'):
                    assert elem.is_hidden != bool_
