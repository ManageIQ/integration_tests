import re

import attr
from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import Checkbox
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.common import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


class TopologySearch(View):
    """Represents search_text control of TopologyView."""

    search_input = Input(id='search_topology')
    search_button = Button(**{
        'data-function-data': '{"service":"topologyService","name":"searchNode"}'
    })
    # Text widget is used here due missing 'btn' class
    clear_button = Text(".//button[@data-function-data="
                        "'{\"service\":\"topologyService\",\"name\":\"resetSearch\"}']")

    def clear_search(self):
        self.clear_button.click()

    def search(self, text):
        self.search_input.fill(text)
        self.search_button.click()


class TopologyToolbar(View):
    display_names = Checkbox("Display Names")
    search_box = View.nested(TopologySearch)
    refresh = Button("Refresh")


class BaseTopologyView(BaseLoggedInPage):
    """Represents a topology page."""

    toolbar = View.nested(TopologyToolbar)

    @ParametrizedView.nested
    class legends(ParametrizedView):  # noqa
        PARAMETERS = ('name', )
        ALL_LEGENDS = './/kubernetes-topology-icon//label'
        el = Text(ParametrizedLocator(
            './/kubernetes-topology-icon//label[normalize-space(.)={name|quote}]'))

        @property
        def is_enabled(self):
            el = self.browser.element('./ancestor::kubernetes-topology-icon[1]', self.el)
            return 'active' in self.browser.get_attribute('class', el)

        def enable(self):
            if not self.is_enabled:
                self.el.click()

        def disable(self):
            if self.is_enabled:
                self.el.click()

        @property
        def name(self):
            return self.el.text

        @classmethod
        def all(cls, browser):
            return [(browser.text(e), ) for e in browser.elements(cls.ALL_LEGENDS)]

    @ParametrizedView.nested
    class elements(ParametrizedView):  # noqa
        PARAMETERS = ('name', 'type')
        EXPRESSION = 'Name: (.*) Type: (.*) Status: (.*)'
        ALL_ELEMENTS = './/kubernetes-topology-graph//*[name()="g"]'
        el = Text(ParametrizedLocator(
            './/kubernetes-topology-graph/'
            '/*[name()="g" and @class={type|quote}]/'
            '*[name()="text" and contains(text(), {name|quote})]/..'
        ))

        @property
        def is_opaqued(self):
            return 'opacity: 0.2' in self.browser.get_attribute('style', self.el)

        def double_click(self):
            self.browser.double_click(self.el)

        @property
        def x(self):
            return round(float(self.browser.get_attribute('cx', self.el)), 1)

        @property
        def y(self):
            return round(float(self.browser.get_attribute('cy', self.el)), 1)

        @property
        def name(self):
            text = self.browser.text(self.browser.element('./*[name()="title"]', self.el))
            return re.search(self.EXPRESSION, text).group(1)

        @property
        def type(self):
            return self.browser.get_attribute('class', self.el)

        @classmethod
        def all(cls, browser):
            result = []
            for e in browser.elements(cls.ALL_ELEMENTS):
                text = browser.text(browser.element('./*[name()="title"]', parent=e))
                name = re.search(cls.EXPRESSION, text).group(1)
                type_ = browser.get_attribute('class', e)
                result.append((name, type_))
            return result

    @property
    def is_displayed(self):
        obj = self.context["object"]
        return (
            self.logged_in_as_current_user
            and self.toolbar.is_displayed
            and self.navigation.currently_selected
            == ["Compute", "Clouds" if obj.string_name == "Cloud" else obj.string_name, "Topology"]
        )


@attr.s
class BaseTopologyElement(BaseEntity):
    """Represents Topology Element
       Consists of Browser element and its parent Topology
    """
    name = attr.ib()
    type = attr.ib()

    def double_click(self):
        self.parent._view.elements(self.name, self.type).double_click()

    @property
    def is_opaqued(self):
        return self.parent._view.elements(self.name, self.type).is_opaqued

    @property
    def x(self):
        return self.parent._view.elements(self.name, self.type).x

    @property
    def y(self):
        return self.parent._view.elements(self.name, self.type).y

    @property
    def is_displayed(self):
        return self.parent._view.elements(self.name, self.type).is_displayed


@attr.s
class BaseTopologyElementsCollection(BaseCollection):
    """Collection object for elements in topology"""

    ENTITY = BaseTopologyElement

    @property
    def _view(self):
        return navigate_to(self, 'All')

    @property
    def legends(self):
        return [legend_el.name for legend_el in list(self._view.legends)]

    def is_legend_enabled(self, legend_name):
        return self._view.legends(legend_name).is_enabled

    def enable_legend(self, legend_name):
        self._view.legends(legend_name).enable()

    def disable_legend(self, legend_name):
        self._view.legends(legend_name).disable()

    def refresh(self):
        self._view.refresh.click()

    @property
    def are_display_names_shown(self):
        return self._view.toolbar.display_names.selected

    def show_display_names(self):
        self._view.toolbar.display_names.fill(True)

    def hide_display_names(self):
        self._view.toolbar.display_names.fill(False)

    def search(self, text):
        self._view.toolbar.search_box.search(text)
        return [el for el in self.all() if not el.is_opaqued]

    def clear_search(self):
        self._view.toolbar.search_box.clear_search()

    def wait_for_movement_stop(self):
        element = self.all()[-1]

        def _compare_coordinates(element, coordinates=[]):
            if coordinates == [element.x, element.y]:
                return True
            else:
                coordinates = [element.x, element.y]

        wait_for(
            _compare_coordinates,
            func_args=[element],
            timeout=10,
            delay=2
        )

    def all(self):
        return [self.instantiate(el.name, el.type) for el in list(self._view.elements)]
