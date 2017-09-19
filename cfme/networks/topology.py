import re
import time

from navmazing import NavigateToAttribute

from cfme.networks.topology_view import TopologyView
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from wait_for import wait_for


class Topology(Navigatable):
    LEGENDS = '//kubernetes-topology-icon'
    ELEMENTS = '//kubernetes-topology-graph//*[name()="g"]'
    LINES = '//kubernetes-topology-graph//*[name()="lines_obj"]'

    def __init__(self, appliance):
        Navigatable.__init__(self, appliance=appliance)
        self.legends_obj = []
        self.elements_obj = []
        self.lines_obj = []
        self.element_ref = None
        self.display_names = None
        self.view = None

        self.reload_view()
        self.refresh()
        self.reload_elements_and_lines()
        self.reload_legends()

    def __repr__(self):
        return "<Topology {}>".format(", ".join(self._legends_obj))

    def reload_view(self):
        self.view = navigate_to(self, 'All')

    def refresh(self):
        self.view.toolbar.refresh.click()
        time.sleep(5)
        self.reload_elements_and_lines()

    def reload_elements_and_lines(self):
        self.elements_obj = []
        self.lines_obj = []
        found_elements = self.browser.elements(self.ELEMENTS)

        if found_elements:
            self.element_ref = TopologyElement(obj=self, element=found_elements[-1])
            wait_for(lambda: self.movement_stopped(), delay=2, num_sec=30)

            for element in found_elements:
                self.elements_obj.append(TopologyElement(obj=self, element=element))

            for line in self.browser.elements(self.LINES):
                self.lines_obj.append(TopologyLine(element=line))

    def reload_legends(self):
        self.legends_obj = []
        self.display_names = TopologyDisplayNames(self)

        found_legends = self.browser.elements(self.LEGENDS)
        for legend in found_legends:
            legend_text = self.browser.text(legend.find_element_by_tag_name('label'))

            legend_object = TopologyLegend(name=legend_text, element=legend)
            self.legends_obj.append(legend_object)

    def movement_stopped(self):
        element = TopologyElement(obj=self, element=self.browser.elements(self.ELEMENTS)[-1])
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


class TopologyLegend(object):
    def __init__(self, name, element):
        self.legend_name = name
        self.element = element

    @property
    def name(self):
        return self.legend_name

    @property
    def is_active(self):
        return 'active' in self.element.get_attribute('class')

    def set_active(self, active=True):
        if active != self.is_active:
            self.element.click()


class TopologyDisplayNames(object):
    DISPLAY_NAME = '|'.join([
        "//*[contains(@class, 'container_topology')]//label[contains(., 'Display Names')]/input",
        '//*[@id="box_display_names"]'])  # [0] is not working on containers topology

    def __init__(self, obj):
        self.element = obj.browser.element(self.DISPLAY_NAME)

    @property
    def is_enabled(self):
        return self.element.is_selected()

    def enable(self, enable=True):
        if self.is_enabled != enable:
            self.element.click()

    def disable(self):
        self.enable(enable=False)


class TopologyElement(object):
    def __init__(self, obj, element):
        if element is None:
            raise KeyError('Element should not be None')
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


class TopologyLine(object):
    def __init__(self, element):
        if element is None:
            raise KeyError('Element should not be None')
        self.connection = element.get_attribute('class')
        self.x1 = round(float(element.get_attribute('x1')), 1)
        self.x2 = round(float(element.get_attribute('x2')), 1)
        self.y1 = round(float(element.get_attribute('y1')), 1)
        self.y2 = round(float(element.get_attribute('y2')), 1)

    def __repr__(self):
        return "<Topologylines_obj Connection:{}, x1,y1:{},{}, x2,y2:{},{}>".format(
            self.connection, self.x1, self.y1, self.x2, self.y2)
