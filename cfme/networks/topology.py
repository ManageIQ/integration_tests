import re
import attr

from navmazing import NavigateToAttribute

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.networks.topology_view import TopologyView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.wait import wait_for


@attr.s
class TopologyLegend(BaseEntity):
    """ Class representing Topology Legend
        Consists of Browser element and its name
    """
    element = attr.ib()
    legend_name = attr.ib()

    @property
    def name(self):
        return self.legend_name

    @property
    def is_active(self):
        return 'active' in self.element.get_attribute('class')

    def set_active(self, active=True):
        if active != self.is_active:
            self.element.click()


@attr.s
class TopologyLegendCollection(BaseCollection):
    """Collection object for legends in topology"""
    ENTITY = TopologyLegend

    def filter(self, topology):
        final_legends = []
        legends = topology.browser.elements(topology.view.LEGENDS)
        for element in legends:
            legend_name = topology.browser.text(element.find_element_by_tag_name('label'))
            final_legends.append(self.instantiate(element, legend_name))
        return final_legends


@attr.s
class TopologyDisplayNames(BaseEntity):
    """ Class representing Displaying buttons of legends
        Consists of Browser element
    """
    element = attr.ib()

    @property
    def is_enabled(self):
        return self.element.is_selected()

    def enable(self, enable=True):
        if self.is_enabled != enable:
            self.element.click()

    def disable(self):
        self.enable(enable=False)


@attr.s
class TopologyElement(BaseEntity):
    """ Class representing Topology Element
        Consists of Browser element and its parent Topology
    """
    element = attr.ib()
    obj = attr.ib()

    @property
    def is_hidden(self):
        return 'opacity: 0.2' in self.element.get_attribute('style')

    @property
    def parents(self):
        elements_obj = []
        for lines_obj in [lines_obj for lines_obj in self.object.lines_obj()
                          if lines_obj.x2 == self.x and lines_obj.y2 == self.y]:
                for element in self.object.elements_obj():
                    if element.x == lines_obj.x1 and element.y == lines_obj.y1:
                        elements_obj.append(element)
        return elements_obj

    @property
    def children(self):
        elements_obj = []
        for lines_obj in [lines_obj for lines_obj in self.object.lines_obj()
                          if lines_obj.x1 == self.x and lines_obj.y1 == self.y]:
            for element in self.object.elements_obj():
                if element.x == lines_obj.x2 and element.y == lines_obj.y2:
                    elements_obj.append(element)
        return elements_obj

    def double_click(self):
        self.obj.browser.double_click(self.element)

    def is_displayed(self):
        try:
            return self.element.is_displayed()
        except Exception:
            return False


@attr.s
class TopologyElementCollection(BaseCollection):
    """Collection object for elements in topology"""
    ENTITY = TopologyElement

    def instantiate(self, *args, **kwargs):
        elem = super(TopologyElementCollection, self).instantiate(*args, **kwargs)
        assert elem.element, 'Element should not be None'
        element_data = re.search('Name: (.*) Type: (.*) Status: (.*)', elem.element.text)
        assert len(element_data.groups()) == 3, 'Topology element doesnt have name, type or status'
        elem.name = element_data.group(1)
        elem.type = element_data.group(2)
        elem.status = element_data.group(3)
        elem.x = round(float(elem.element.get_attribute('cx')), 1)
        elem.y = round(float(elem.element.get_attribute('cy')), 1)
        return elem

    def filter(self, obj):
        elements = obj.browser.elements(obj.view.ELEMENTS)
        return [self.instantiate(element, obj) for element in elements]


@attr.s
class TopologyLine(BaseEntity):
    """ Class representing line connecting 2 nodes in Topology
        Consists of Browser element
    """
    element = attr.ib()


@attr.s
class TopologyLineCollection(BaseCollection):
    """Collection object for lines in topology"""
    ENTITY = TopologyLine

    def instantiate(self, *args, **kwargs):
        line = super(TopologyLineCollection, self).instantiate(*args, **kwargs)
        assert line.element, 'Element should not be None'
        line.connection = line.element.get_attribute('class')
        line.x1 = round(float(line.element.get_attribute('x1')), 1)
        line.x2 = round(float(line.element.get_attribute('x2')), 1)
        line.y1 = round(float(line.element.get_attribute('y1')), 1)
        line.y2 = round(float(line.element.get_attribute('y2')), 1)
        return line

    def filter(self, topology):
        lines = topology.browser.elements(topology.view.LINES)
        return [self.instantiate(element=line) for line in lines]


@attr.s
class Topology(BaseEntity):
    "Class represents SDN topology"
    elements_obj = attr.ib(default=[])
    lines_obj = attr.ib(default=[])
    legends_obj = attr.ib(default=[])
    elements_col = attr.ib(default=None)
    lines_col = attr.ib(default=None)
    legends_col = attr.ib(default=None)
    element_ref = attr.ib(default=None)
    display_names = attr.ib(default=None)
    view = attr.ib(default=None)

    def reload_elements_and_lines(self):
        self.elements_obj = []
        self.lines_obj = self.lines_col.filter(self)
        found_elements = self.elements_col.filter(self)

        if found_elements:
            self.element_ref = found_elements[-1]
            wait_for(lambda: self.movement_stopped, delay=2, num_sec=30)
            self.elements_obj = self.elements_col.filter(self)

    def reload_legends(self):
        self.legends_obj = self.legends_col.filter(self)
        element = self.browser.element(self.view.DISPLAY_NAME)
        self.display_names = TopologyDisplayNames(self.appliance, element)

    @property
    def movement_stopped(self):
        element = self.elements_col.filter(self)[-1]
        if element.x == self.element_ref.x and element.y == self.element_ref.y:
            return True
        self.element_ref = element
        return False

    @property
    def legends(self):
        return self.legends_obj

    @property
    def elements(self):
        return self.elements_obj

    @property
    def lines(self):
        return self.lines_obj


@attr.s
class TopologyCollection(BaseCollection):
    """Collection object for elements in topology"""
    ENTITY = Topology

    def instantiate(self, *args, **kwargs):
        topology = super(TopologyCollection, self).instantiate(*args, **kwargs)
        topology.elements_col = TopologyElementCollection(topology)
        topology.lines_col = TopologyLineCollection(topology)
        topology.legends_col = TopologyLegendCollection(topology)
        topology.view = navigate_to(topology, 'All')
        topology.reload_elements_and_lines()
        topology.reload_legends()
        return topology


@navigator.register(Topology, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = TopologyView

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Topology')
