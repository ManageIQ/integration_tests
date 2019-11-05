# -*- coding: utf-8 -*-
"""A model of an Infrastructure PhysicalStorage in CFME."""
import attr
from cached_property import cached_property
from lxml.html import document_fromstring
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import SummaryTable


class ComputePhysicalInfrastructureStoragesView(BaseLoggedInPage):
    """Common parts for Storage views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_compute_physical_infrastructure_storages(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Storages"])


class PhysicalStorageEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(PhysicalStorageEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            quad_data = document_fromstring(data_dict['quadicon'])
            data_dict['no_port'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
            data_dict['state'] = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].get('style')
            data_dict['vendor'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].get('alt')
            data_dict['health_state'] = quad_data.xpath(self.QUADRANT.format(pos="d"))[0].get('alt')
        return data_dict


class PhysicalStorageDetailsToolbar(View):
    """Represents physical toolbar and its controls."""
    configuration = Dropdown(text="Configuration")


class PhysicalStorageDetailsEntities(View):
    """Represents Details page."""
    properties = SummaryTable(title="Properties")
    management_networks = SummaryTable(title="Management Networks")
    relationships = SummaryTable(title="Relationships")
    power_management = SummaryTable(title="Power Management")
    firmwares = SummaryTable(title="Firmwares")
    ports = SummaryTable(title="Ports")


class PhysicalStorageDetailsView(ComputePhysicalInfrastructureStoragesView):
    """Main PhysicalStorage details page."""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(PhysicalStorageDetailsToolbar)
    entities = View.nested(PhysicalStorageDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (self.in_compute_physical_infrastructure_storages and
                self.breadcrumb.active_location == title)


class PhysicalStoragesToolbar(View):
    """Represents hosts toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    view_selector = View.nested(ItemsToolBarViewSelector)


class PhysicalStorageSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""

    @View.nested
    class filters(Accordion): # noqa
        tree = ManageIQTree()


class PhysicalStorageEntitiesView(BaseEntitiesView):
    """Represents the physical storage view"""
    @property
    def entity_class(self):
        return PhysicalStorageEntity


class PhysicalStoragesView(ComputePhysicalInfrastructureStoragesView):
    toolbar = View.nested(PhysicalStoragesToolbar)
    sidebar = View.nested(PhysicalStorageSideBar)
    including_entities = View.include(PhysicalStorageEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_storages and
                self.title.text == "Physical Storages")


@attr.s
class PhysicalStorage(BaseEntity, Updateable, Pretty, PolicyProfileAssignable, Taggable):
    """Model of an Physical Storage in cfme.

    Args:
        name: Name of the physical storage.

    Usage:
        mystorage = PhysicalStorage(name='sample_Storage')
        mystorage.create()

    """
    pretty_attrs = ['name']

    name = attr.ib()
    provider = attr.ib()

    INVENTORY_TO_MATCH = ['Product Name', 'Serial Number', 'Description',
                          'Health State', 'Drive Bays', 'Enclosure Count']

    def get_value_from_summary(self, value):
        """Returns the value of a summary table

        Usage:
            mystorage = PhysicalStorage(name='sample_Storage')
            mystorage.get_value_from_summary(value)

        Args:
            value (str): The Storage property you want to retrieve from Details page.
        """
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of(value)

    def exists(self):
        """Checks if the physical_Storage exists in the UI.

        Returns: :py:class:`bool`
        """
        view = navigate_to(self.parent, "All")
        try:
            view.entities.get_entity(name=self.name, surf_pages=True)
            return True
        except ItemNotFound:
            return False

    @cached_property
    def db_id(self):
        return self.appliance.physical_storage_id(self.name)


@attr.s
class PhysicalStorageCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.PhysicalStorage`."""

    ENTITY = PhysicalStorage

    def select_entity_rows(self, *physical_storages):
        """ Select all physical storage objects """
        view = navigate_to(self, 'All')

        for physical_storage in physical_storages:
            view.entities.get_entity(name=physical_storage.name, surf_pages=True).check()

    def all(self):
        """returning all physical_storages objects"""
        physical_storage_table = self.appliance.db.client['physical_storages']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_storage_query = (
            self.appliance.db.client.session
                .query(physical_storage_table.name, ems_table.name)
                .join(ems_table, physical_storage_table.id == ems_table.id))
        provider = self.filters.get('provider')
        if provider:
            physical_storage_query = physical_storage_query.filter(ems_table.name == provider.name)
        physical_storages = []
        for name, ems_name in physical_storage_query.all():
            physical_storages.append(self.instantiate(name=name,
                                    provider=provider or get_crud_by_name(ems_name)))
        return physical_storages


@navigator.register(PhysicalStorageCollection, 'All')
class All(CFMENavigateStep):
    VIEW = PhysicalStoragesView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Storages")


@navigator.register(PhysicalStorage, 'Detail')
class Details(CFMENavigateStep):
    VIEW = PhysicalStorageDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
