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
    ManageIQTree
)
from widgetastic_patternfly import Dropdown, Accordion
from widgetastic.widget import ParametrizedView, Text, View

from cfme.base.login import BaseLoggedInPage


class ComputePhysicalInfrastructureRacksView(BaseLoggedInPage):
    """Common parts for rack views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_compute_physical_infrastructure_racks(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Racks"])


class PhysicalRackQuadIconEntity(BaseQuadIconEntity):
    @property
    def data(self):
        return {
            'no_physical_servers': int(self.browser.text(self.QUADRANT.format(pos="a"))),
        }


class PhysicalRackTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(PhysicalRackQuadIconEntity)


class PhysicalRackListEntity(BaseListEntity):
    pass


class NonJSPhysicalRackEntity(NonJSBaseEntity):
    quad_entity = PhysicalRackQuadIconEntity
    list_entity = PhysicalRackListEntity
    tile_entity = PhysicalRackTileIconEntity


class PhysicalRackEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(PhysicalRackEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            quad_data = document_fromstring(data_dict['quadicon'])
            data_dict['no_host'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
        return data_dict


class PhysicalRackDetailsToolbar(View):
    """Represents physical rack toolbar and its controls."""
    configuration_button = Dropdown(text="Configuration")


class PhysicalRackDetailsEntities(View):
    """Represents Details page Entities."""
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")


class PhysicalRackDetailsView(ComputePhysicalInfrastructureRacksView):
    """Main PhysicalRack details page."""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(PhysicalRackDetailsToolbar)
    entities = View.nested(PhysicalRackDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (self.in_compute_physical_infrastructure_racks and
                self.breadcrumb.active_location == title)


class PhysicalRacksToolbar(View):
    """Represents hosts toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    view_selector = View.nested(ItemsToolBarViewSelector)


class PhysicalRackSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""

    @View.nested
    class filters(Accordion): # noqa
        tree = ManageIQTree()


class PhysicalRackEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return PhysicalRackEntity().pick(self.browser.product_version)


class PhysicalRacksView(ComputePhysicalInfrastructureRacksView):
    toolbar = View.nested(PhysicalRacksToolbar)
    sidebar = View.nested(PhysicalRackSideBar)
    including_entities = View.include(PhysicalRackEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_racks and
                self.title.text == "Physical Racks")
