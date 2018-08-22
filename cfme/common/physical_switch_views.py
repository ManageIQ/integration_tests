# -*- coding: utf-8 -*-
from lxml.html import document_fromstring
from widgetastic_manageiq import (
    BaseEntitiesView,
    NonJSBaseEntity,
    JSBaseEntity,
    BaseListEntity,
    BaseQuadIconEntity,
    BaseTileIconEntity,
    BreadCrumb,
    ItemsToolBarViewSelector,
    SummaryTable,
    TimelinesView,
    ManageIQTree
)
from widgetastic_patternfly import Dropdown, Accordion
from widgetastic.utils import Parameter
from widgetastic.widget import ParametrizedView, Text, View

from cfme.base.login import BaseLoggedInPage


class ComputePhysicalInfrastructureSwitchesView(BaseLoggedInPage):
    """Common parts for switch views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_compute_physical_infrastructure_switches(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Switches"])


class PhysicalSwitchQuadIconEntity(BaseQuadIconEntity):
    @property
    def data(self):
        return {
            'no_port': int(self.browser.text(self.QUADRANT.format(pos="a"))),
            'state': self.browser.get_attribute("style", self.QUADRANT.format(pos="b")),
            'vendor': self.browser.get_attribute("alt", self.QUADRANT.format(pos="c")),
            'health_state': self.browser.get_attribute("alt", self.QUADRANT.format(pos="d"))
        }


class PhysicalSwitchTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(PhysicalSwitchQuadIconEntity)


class PhysicalSwitchListEntity(BaseListEntity):
    pass


class NonJSPhysicalSwitchEntity(NonJSBaseEntity):
    quad_entity = PhysicalSwitchQuadIconEntity
    list_entity = PhysicalSwitchListEntity
    tile_entity = PhysicalSwitchTileIconEntity


class PhysicalSwitchEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(PhysicalSwitchEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            quad_data = document_fromstring(data_dict['quadicon'])
            data_dict['no_port'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
            data_dict['state'] = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].get('style')
            data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('alt')
            data_dict['health_state'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].get('alt')
        return data_dict


class PhysicalSwitchDetailsToolbar(View):
    """Represents physical toolbar and its controls."""
    configuration = Dropdown(text="Configuration")

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group", )
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=False):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class PhysicalSwitchDetailsEntities(View):
    """Represents Details page."""
    properties = SummaryTable(title="Properties")
    management_networks = SummaryTable(title="Management Networks")
    relationships = SummaryTable(title="Relationships")
    power_management = SummaryTable(title="Power Management")
    firmwares = SummaryTable(title="Firmwares")
    ports = SummaryTable(title="Ports")


class PhysicalSwitchDetailsView(ComputePhysicalInfrastructureSwitchesView):
    """Main PhysicalSwitch details page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    toolbar = View.nested(PhysicalSwitchDetailsToolbar)
    entities = View.nested(PhysicalSwitchDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (self.in_compute_physical_infrastructure_switches and
                self.breadcrumb.active_location == title)


class PhysicalSwitchTimelinesView(TimelinesView, ComputePhysicalInfrastructureSwitchesView):
    """Represents a PhysicalSwitch Timelines page."""

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_switches and
                super(TimelinesView, self).is_displayed)


class PhysicalSwitchProvisionView(BaseLoggedInPage):
    """Represents the Provision Physical Switch page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')

    @property
    def is_displayed(self):
        title = "Add PhysicalSwitch"
        return self.breadcrumb.active_location == title


class PhysicalSwitchesToolbar(View):
    """Represents hosts toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    view_selector = View.nested(ItemsToolBarViewSelector)

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group",)
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=False):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class PhysicalSwitchSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""

    @View.nested
    class filters(Accordion): # noqa
        tree = ManageIQTree()


class PhysicalSwitchEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return PhysicalSwitchEntity


class PhysicalSwitchesView(ComputePhysicalInfrastructureSwitchesView):
    toolbar = View.nested(PhysicalSwitchesToolbar)
    sidebar = View.nested(PhysicalSwitchSideBar)
    including_entities = View.include(PhysicalSwitchEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_switches and
                self.title.text == "Physical Switches")
