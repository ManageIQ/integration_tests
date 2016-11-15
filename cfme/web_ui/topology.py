import re
from cfme.fixtures import pytest_selenium as sel
from selenium.common.exceptions import ElementNotVisibleException, StaleElementReferenceException
from utils import attributize_string
from utils.browser import ensure_browser_open
from wait_for import wait_for


class Topology(object):
    LEGENDS = '//kubernetes-topology-icon'
    ELEMENTS = '//kubernetes-topology-graph//*[name()="g"]'
    LINES = '//kubernetes-topology-graph//*[name()="line"]'

    def __init__(self, o):
        self._object = o
        self._legends = []
        self._elements = []
        self._lines = []
        self._el_ref = None
        self.search_box = None
        self.display_names = None
        self.reload()

    def __repr__(self):
        return "<Topology {}>".format(", ".join(self._legends))

    def reload(self):
        ensure_browser_open()
        self._object.load_topology_page()
        self._reload()

    def refresh(self):
        ensure_browser_open()
        sel.click("//*[contains(@class, 'container_topology')]//button[contains(., 'Refresh')]")
        self._reload()

    def _is_el_movement_stopped(self):
        _el = TopologyElement(o=self, element=sel.elements(self.ELEMENTS)[-1])
        if _el.x == self._el_ref.x and _el.y == self._el_ref.y:
            return True
        self._el_ref = _el
        return False

    def reload_elements(self):
        self._elements = []
        self._lines = []
        if len(sel.elements(self.ELEMENTS)) > 0:
            self._el_ref = TopologyElement(o=self, element=sel.elements(self.ELEMENTS)[-1])
            wait_for(lambda: self._is_el_movement_stopped(), delay=2, num_sec=30)

            for element in sel.elements(self.ELEMENTS):
                self._elements.append(TopologyElement(o=self, element=element))
            # load lines
            for line in sel.elements(self.LINES):
                self._lines.append(TopologyLine(element=line))

    def _reload(self):
        self._legends = []
        self.search_box = TopologySearchBox()
        self.display_names = TopologyDisplayNames()
        # load elements
        # we have to wait few seconds, initial few seconds elements are moving
        self.reload_elements()
        # load legends
        # remove old legends
        for legend_id in self._legends:
            try:
                delattr(self, legend_id)
            except AttributeError:
                pass
        # load available legends
        for legend in sel.elements(self.LEGENDS):
            legend_text = sel.text_sane(legend.find_element_by_tag_name('label'))
            legend_id = attributize_string(legend_text.strip())
            legend_object = TopologyLegend(name=legend_text, element=legend)
            setattr(self, legend_id, legend_object)
            self._legends.append(legend_id)

    def __iter__(self):
        """This enables you to iterate through like it was a dictionary, just without .iteritems"""
        for legend_id in self._legends:
            yield (legend_id, getattr(self, legend_id))

    @property
    def legends(self):
        return self._legends

    def elements(self, element_type=None):
        if element_type:
            return [el for el in self._elements if el.type == element_type]
        return self._elements

    def lines(self, connection=None):
        if connection:
            return [ln for ln in self._lines if ln.connection == connection]
        return self._lines


class TopologyLegend(object):
    def __init__(self, name, element):
        self._name = name
        self._element = element

    @property
    def name(self):
        return self._name

    @property
    def is_active(self):
        return 'active' in self._element.get_attribute('class')

    def set_active(self, active=True):
        if active != self.is_active:
            self._element.click()


class TopologyDisplayNames(object):
    DISPLAY_NAME = '|'.join([
        "//*[contains(@class, 'container_topology')]//label[contains(., 'Display Names')]/input",
        '//*[@id="box_display_names"]'])  # [0] is not working on containers topology

    def __init__(self):
        self._el = sel.element(self.DISPLAY_NAME)

    @property
    def is_enabled(self):
        return self._el.is_selected()

    def enable(self, enable=True):
        if self.is_enabled != enable:
            self._el.click()

    def disable(self):
        self.enable(enable=False)


class TopologySearchBox(object):
    SEARCH_BOX = "//input[@id='search_topology']|//input[@id='search']"
    SEARCH_CLEAR = "//button[contains(@class, 'clear')]"
    SEARCH_SUBMIT = "//button[contains(@class, 'search-topology-button')]"

    def clear(self):
        try:
            sel.element(self.SEARCH_CLEAR).click()
        except ElementNotVisibleException:
            pass

    def submit(self):
        sel.element(self.SEARCH_SUBMIT).click()

    def text(self, submit=True, text=None):
        if text is not None:
            self.clear()
            sel.element(self.SEARCH_BOX).send_keys(text)
            if submit:
                self.submit()
        else:
            return sel.element(self.SEARCH_BOX).text


class TopologyElement(object):
    def __init__(self, o, element):
        if element is None:
            raise KeyError('Element should not be None')
        self.sel_element = element
        self._object = o
        el_data = re.search('Name: (.*) Type: (.*) Status: (.*)', element.text)
        if len(el_data.groups()) != 3:
            raise RuntimeError('Unexpected element')
        self.name = el_data.group(1)
        self.type = el_data.group(2)
        self.status = el_data.group(3)
        self.x = round(float(element.get_attribute('cx')), 1)
        self.y = round(float(element.get_attribute('cy')), 1)

    def __repr__(self):
        return "<TopologyElement name:{}, type:{}, status:{}, x:{}, y:{}, is_hidden:{}>".format(
            self.name, self.type, self.status, self.x, self.y, self.is_hidden)

    @property
    def is_hidden(self):
        return 'opacity: 0.2' in self.sel_element.get_attribute('style')

    @property
    def parents(self):
        elements = []
        for line in [_line for _line in self._object.lines()
                     if _line.x2 == self.x and _line.y2 == self.y]:
            for _el in self._object.elements():
                if _el.x == line.x1 and _el.y == line.y1:
                    elements.append(_el)
        return elements

    @property
    def children(self):
        elements = []
        for line in [_line for _line in self._object.lines()
                     if _line.x1 == self.x and _line.y1 == self.y]:
            for _el in self._object.elements():
                if _el.x == line.x2 and _el.y == line.y2:
                    elements.append(_el)
        return elements

    def double_click(self):
        sel.double_click(self.sel_element)

    def is_displayed(self):
        try:
            return self.sel_element.is_displayed()
        except StaleElementReferenceException:
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
        return "<TopologyLine Connection:{}, x1,y1:{},{}, x2,y2:{},{}>".format(
            self.connection, self.x1, self.y1, self.x2, self.y2)
