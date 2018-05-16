# -*- coding: utf-8 -*-
from lxml.html import document_fromstring
from widgetastic.utils import (
    Parameter, Version, VersionPick)
from widgetastic.widget import ParametrizedView, Text, View
from widgetastic_patternfly import (
    BreadCrumb, Dropdown, Accordion)

from cfme.base.login import BaseLoggedInPage
from widgetastic_manageiq import (
    BaseEntitiesView, NonJSBaseEntity, JSBaseEntity, BaseListEntity, BaseQuadIconEntity,
    BaseTileIconEntity, BootstrapTreeview, Button, ItemsToolBarViewSelector, SummaryTable,
    TimelinesView, BaseNonInteractiveEntitiesView, ManageIQTree)


class ComputePhysicalInfrastructureServersView(BaseLoggedInPage):
    """Common parts for server views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_compute_physical_infrastructure_servers(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Servers"])


class PhysicalServerQuadIconEntity(BaseQuadIconEntity):
    @property
    def data(self):
        return {
            'no_host': int(self.browser.text(self.QUADRANT.format(pos="a"))),
            'state': self.browser.get_attribute("style", self.QUADRANT.format(pos="b")),
            'vendor': self.browser.get_attribute("alt", self.QUADRANT.format(pos="c")),
            'creds': self.browser.get_attribute("alt", self.QUADRANT.format(pos="d"))
        }


class PhysicalServerTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(PhysicalServerQuadIconEntity)


class PhysicalServerListEntity(BaseListEntity):
    pass


class NonJSPhysicalServerEntity(NonJSBaseEntity):
    quad_entity = PhysicalServerQuadIconEntity
    list_entity = PhysicalServerListEntity
    tile_entity = PhysicalServerTileIconEntity


class JSPhysicalServerEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(JSPhysicalServerEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            quad_data = document_fromstring(data_dict['quadicon'])
            data_dict['no_host'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
            data_dict['state'] = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].get('style')
            data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('alt')
            data_dict['creds'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].get('alt')
        return data_dict


def PhysicalServerEntity():  # noqa
    """ Temporary wrapper for PhysicalServer Entity during transition to JS based Entity

    """
    return VersionPick({
        Version.lowest(): NonJSPhysicalServerEntity,
        '5.9': JSPhysicalServerEntity,
    })


class PhysicalServerDetailsToolbar(View):
    """Represents physical toolbar and its controls."""
    monitoring = Dropdown(text="Monitoring")
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    power = Dropdown(text="Power")
    identify = Dropdown(text="Identify")
    lifecycle = Dropdown(text="Lifecycle")

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group", )
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=False):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class PhysicalServerDetailsEntities(View):
    """Represents Details page."""
    properties = SummaryTable(title="Properties")
    networks = SummaryTable(title="Networks")
    relationships = SummaryTable(title="Relationships")
    power_management = SummaryTable(title="Power Management")
    assets = SummaryTable(title="Assets")
    firmware = SummaryTable(title="Firmware")
    network_devices = SummaryTable(title="Network Devices")
    smart = SummaryTable(title="Smart Management")


class PhysicalServerDetailsView(ComputePhysicalInfrastructureServersView):
    """Main PhysicalServer details page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')
    toolbar = View.nested(PhysicalServerDetailsToolbar)
    entities = View.nested(PhysicalServerDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (self.in_compute_physical_infrastructure_servers and
                self.breadcrumb.active_location == title)


class PhysicalServerTimelinesView(TimelinesView, ComputePhysicalInfrastructureServersView):
    """Represents a PhysicalServer Timelines page."""

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_servers and
                super(TimelinesView, self).is_displayed)


class PhysicalServerProvisionView(BaseLoggedInPage):
    """Represents the Provision Physical Server page."""
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')

    @property
    def is_displayed(self):
        title = "Add PhysicalServer"
        return self.breadcrumb.active_location == title


class PhysicalServerManagePoliciesView(BaseLoggedInPage):
    """PhysicalServer's Manage Policies view."""
    policies = BootstrapTreeview("protectbox")
    entities = View.nested(BaseNonInteractiveEntitiesView)
    save = Button("Save")
    reset = Button("Reset")
    cancel = Button("Cancel")
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')

    @property
    def is_displayed(self):
        title = "'Physical Server' Policy Assignment"
        return self.breadcrumb.active_location == title


class PhysicalServerEditTagsView(BaseLoggedInPage):
    """PhysicalServer's EditTags view."""
    policies = BootstrapTreeview("protectbox")
    entities = View.nested(BaseNonInteractiveEntitiesView)
    breadcrumb = BreadCrumb(locator='.//ol[@class="breadcrumb"]')

    @property
    def is_displayed(self):
        title = "Tag Assignment"
        return self.breadcrumb.active_location == title


class PhysicalServersToolbar(View):
    """Represents hosts toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    policy = Dropdown(text="Policy")
    lifecycle = Dropdown(text="Lifecycle")
    monitoring = Dropdown(text="Monitoring")
    power = Dropdown(text="Power")
    identify = Dropdown(text="Identify")
    view_selector = View.nested(ItemsToolBarViewSelector)

    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ("button_group",)
        _dropdown = Dropdown(text=Parameter("button_group"))

        def item_select(self, button, handle_alert=False):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class PhysicalServerSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""

    @View.nested
    class filters(Accordion): # noqa
        tree = ManageIQTree()


class PhysicalServerEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return PhysicalServerEntity().pick(self.browser.product_version)


class PhysicalServersView(ComputePhysicalInfrastructureServersView):
    toolbar = View.nested(PhysicalServersToolbar)
    sidebar = View.nested(PhysicalServerSideBar)
    including_entities = View.include(PhysicalServerEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_servers and
                self.title.text == "Physical Servers")


class PhysicalServerNetworkDevicesView(ComputePhysicalInfrastructureServersView):
    """Represents the Network Devices page"""

    @property
    def is_displayed(self):
        return ("Network Devices" in self.title.text and
                self.in_compute_physical_infrastructure_servers)


class PhysicalServerStorageDevicesView(ComputePhysicalInfrastructureServersView):
    """Represents the Storage Devices page"""

    @property
    def is_displayed(self):
        return ("Storage Devices" in self.title.text and
                self.in_compute_physical_infrastructure_servers)
