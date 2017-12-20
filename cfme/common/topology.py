import attr
import re
from cached_property import cached_property
from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import Checkbox, ParametrizedView, Text, View
from widgetastic_patternfly import Button, Input

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


class TopologySearch(View):
    """Represents search_text control of TopologyView."""

    _search_text_old = Input(id='search')
    _search_text = Input(id='search_topology')
    _search_btn_old = Button(**{'ng-click': 'searchNode()'})
    _search_btn = Button(**{
        'data-function-data': '"{"service":"topologyService","name":"searchNode"}"'
    })
    _clear_btn_old = Button(**{'ng-click': 'resetSearch()'})
    _clear_btn = Button(**{
        'data-function-data': '"{"service":"topologyService","name":"resetSearch"}"'
    })

    @cached_property
    def search_text(self):
        if self.browser.product_version < '5.9':
            return self._search_text_old
        else:
            return self.search_text

    @cached_property
    def clear(self):
        if self.browser.product_version < '5.9':
            return self._clear_text_old
        else:
            return self.search_text

    def clear_search(self):
        self.clear.click()
        self.search("")

    def search(self, text):
        self.search_text.fill(text)
        self.search_btn.click()


class TopologyToolbar(View):
    display_names = Checkbox("Display Names")
    search_box = View.nested(TopologySearch)
    refresh = Button("Refresh")


class TopologyView(BaseLoggedInPage):
    """Represents a topology page."""

    toolbar = View.nested(TopologyToolbar)

    @ParametrizedView.nested
    class legends(ParametrizedView):  # noqa
        PARAMETERS = ('name', )
        ALL_LEGENDS = './/kubernetes-topology-icon'
        el = Text(
            ParametrizedLocator('{}//label[normalize-space(.)={@name|quote}]'.format(ALL_LEGENDS)))

        @property
        def is_enabled(self):
            return 'active' in self.el.get_attribute('class')

        def enable(self):
            if not self.is_enabled:
                self.el.click()

        def disable(self):
            if self.is_enabled:
                self.el.click()

        @classmethod
        def all(cls, browser):
            return [(browser.text(e), ) for e in browser.elements(cls.ALL_LEGENDS)]

    @ParametrizedView.nested
    class elements(ParametrizedView):
        PARAMETERS = ('name', 'type')
        ALL_ELEMENTS = './/kubernetes-topology-graph//*[name()="g"]'
        el = Text(ParametrizedLocator(
            './/kubernetes-topology-graph/'
            '/*[name()="g" and @class={@type|quote}]/'
            '*[name()="text" and contains(text(), {@name|quote})]/..'
        ))

        @property
        def is_opaqued(self):
            return 'opacity: 0.2' in self.el.get_attribute('style')

        def double_click(self):
            self.browser.double_click(self.el)

        @property
        def x(self):
            return round(float(self.el.get_attribute('cx')), 1)

        @property
        def y(self):
            return round(float(self.el.get_attribute('cy')), 1)

        @classmethod
        def all(cls, browser):
            result = []
            for e in browser.elements(cls.ALL_ELEMENTS):
                text = browser.element('./*[name()="title"]', parent=e)
                e_data = re.search('Name: (.*) Type: (.*)', text)
                result.append((e_data.group(1), e_data.group(2)))
            return result


@attr.s
class BaseTopologyElement(BaseEntity):
    """Represents Topology Element
       Consists of Browser element and its parent Topology
    """
    name = attr.ib()
    type_ = attr.ib()

    def double_click(self):
        self.parent._view.elements(self.name, self.type_).double_click()

    @property
    def is_opaqued(self):
        return self.parent._view.elements(self.name, self.type_).is_opaqued

    @property
    def x(self):
        return self.parent._view.elements(self.name, self.type_).x

    @property
    def y(self):
        return self.parent._view.elements(self.name, self.type_).y


@attr.s
class BaseTopologyElementsCollection(BaseCollection):
    """Collection object for elements in topology"""
    ENTITY = BaseTopologyElement

    @property
    def _view(self):
        return navigate_to(self, 'All')

    @property
    def legends(self):
        return [value[0] for value in list(self._view.legends)]

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

    def wait_until_movement_stopped(self):
        element = self.all()[-1]

        def _compare_coordinates(element, coordinates=[]):
            if coordinates == [element.x, element.y]:
                return True
            else:
                coordinates = [element.x, element.y]

        wait_for(
            lambda: _compare_coordinates
            func_args=[element]
            timeout=10,
            delay=2
        )

    def all(self):
        return [self.instantiate(name, type_) for name, type_ in list(self._view.elements)]
