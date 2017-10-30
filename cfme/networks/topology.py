import re
import attr

from navmazing import NavigateToAttribute

from cfme.networks.topology_view import TopologyView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from wait_for import wait_for


class Topology(BaseEntity):
    "Class represents SDN topology"
    def __init__(self, appliance):
        self.appliance = appliance
        self.elements_obj = []
        self.lines_obj = []
        self.legends_obj = []
        self.elements_col = TopologyElementCollection(self, appliance)
        self.lines_col = TopologyLineCollection(self, appliance)
        self.legends_col = TopologyLegendCollection(self, appliance)
        self.element_ref = None
        self.display_names = None
        self.view = navigate_to(self, 'All')

        self.refresh()
        self.reload_elements_and_lines()
        self.reload_legends()

    def __repr__(self):
        return "<Topology {}>".format(", ".join(self._legends_obj))

    def refresh(self):
        self.view.toolbar.refresh.click()
        self.reload_elements_and_lines()

    def reload_elements_and_lines(self):
        self.elements_obj = []
        self.lines_obj = self.lines_col.all()
        found_elements = self.elements_col.all()

        if found_elements:
            self.element_ref = found_elements[-1]
            wait_for(lambda: self.movement_stopped(), delay=2, num_sec=30)
            self.elements_obj = self.elements_col.all()

    def reload_legends(self):
        self.legends_obj = self.legends_col.all()
        self.display_names = TopologyDisplayNames(self)

    def movement_stopped(self):
        element = self.elements_col.all()[-1]
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


@navigator.register(Topology, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = TopologyView

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Topology')


@attr.s
class TopologyLegend(BaseEntity):
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

    def instantiate(self, name, element):
        return TopologyLegend(legend_name=name, element=element)

    def all(self):
        final_legends = []
        legends = self.topology.browser.elements(self.topology.view.LEGENDS)
        for legend in legends:
            legend_text = self.topology.browser.text(legend.find_element_by_tag_name('label'))
            final_legends.append(self.instantiate(name=legend_text, element=legend))
        return final_legends


class TopologyDisplayNames(BaseEntity):
    def __init__(self, obj):
        self.element = obj.browser.element(obj.view.DISPLAY_NAME)

    @property
    def is_enabled(self):
        return self.element.is_selected()

    def enable(self, enable=True):
        if self.is_enabled != enable:
            self.element.click()

    def disable(self):
        self.enable(enable=False)


class TopologyElement(BaseEntity):
    def __init__(self, obj, element):
        if element is None:
            raise ValueError('Element should not be None')
        self.element = element
        self.object = obj
        element_data = re.search('Name: (.*) Type: (.*) Status: (.*)', element.text)
        if len(element_data.groups()) != 3:
            raise RuntimeError('Topology element does not contain name, type or status')
        self.name = element_data.group(1)
        self.type = element_data.group(2)
        self.status = element_data.group(3)
        self.x = round(float(element.get_attribute('cx')), 1)
        self.y = round(float(element.get_attribute('cy')), 1)

    def __repr__(self):
        return "<TopologyElement name:{}, type:{}, status:{}, x:{}, y:{}, is_hidden:{}>".format(
            self.name, self.type, self.status, self.x, self.y, self.is_hidden)

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

    def instantiate(self, element):
        return TopologyElement(obj=self.topology, element=element)

    def all(self):
        elements = self.topology.browser.elements(self.topology.view.ELEMENTS)
        return [self.instantiate(element=elem) for elem in elements]


class TopologyLine(BaseEntity):
    def __init__(self, element):
        if element is None:
            raise ValueError('Element should not be None')
        self.connection = element.get_attribute('class')
        self.x1 = round(float(element.get_attribute('x1')), 1)
        self.x2 = round(float(element.get_attribute('x2')), 1)
        self.y1 = round(float(element.get_attribute('y1')), 1)
        self.y2 = round(float(element.get_attribute('y2')), 1)

    def __repr__(self):
        return "<Topologylines_obj Connection:{}, x1,y1:{},{}, x2,y2:{},{}>".format(
            self.connection, self.x1, self.y1, self.x2, self.y2)


@attr.s
class TopologyLineCollection(BaseCollection):
    """Collection object for lines in topology"""
    ENTITY = TopologyLine

    def instantiate(self, element):
        return TopologyLine(element=element)

    def all(self):
        lines = self.topology.browser.elements(self.topology.view.LINES)
        return [self.instantiate(element=line) for line in lines]
