""" A model of an Infrastructure Datastore in CFME
"""
import attr
from lxml.html import document_fromstring

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import ParametrizedView, Text, View
from widgetastic_patternfly import Accordion, Dropdown
from widgetastic_manageiq import (
    BaseEntitiesView,
    BaseListEntity,
    BaseQuadIconEntity,
    BaseTileIconEntity,
    ItemsToolBarViewSelector,
    JSBaseEntity,
    ManageIQTree,
    NonJSBaseEntity,
    Search,
    SummaryTable,
)

from cfme.base.login import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common.candu_views import DatastoreInfraUtilizationView
from cfme.common.host_views import HostsView
from cfme.exceptions import ItemNotFound, MenuItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import TimedOutError, wait_for


class DatastoreToolBar(View):
    """
    represents datastore toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    monitoring = Dropdown("Monitoring")
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class DatastoreSideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    @View.nested
    class datastores(Accordion):  # noqa
        ACCORDION_NAME = "Datastores"
        tree = ManageIQTree()

    @View.nested
    class clusters(Accordion):  # noqa
        ACCORDION_NAME = "Datastore Clusters"
        tree = ManageIQTree()


class DatastoreQuadIconEntity(BaseQuadIconEntity):
    @property
    def data(self):
        try:
            return {
                'type': self.browser.get_attribute("alt", self.QUADRANT.format(pos="a")),
                'no_vm': int(self.browser.text(self.QUADRANT.format(pos="b"))),
                'no_host': int(self.browser.text(self.QUADRANT.format(pos="c"))),
            }
        except (IndexError, NoSuchElementException):
            return {}


class DatastoreTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(DatastoreQuadIconEntity)


class DatastoreListEntity(BaseListEntity):
    pass


class NonJSDatastoreEntity(NonJSBaseEntity):
    quad_entity = DatastoreQuadIconEntity
    list_entity = DatastoreListEntity
    tile_entity = DatastoreTileIconEntity


class DatastoreEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(DatastoreEntity, self).data
        try:
            if 'quadicon' in data_dict and data_dict['quadicon']:
                quad_data = document_fromstring(data_dict['quadicon'])
                data_dict['type'] = quad_data.xpath(self.QUADRANT.format(pos="a"))[0].get('alt')
                data_dict['no_vm'] = quad_data.xpath(self.QUADRANT.format(pos="b"))[0].text
                data_dict['no_host'] = quad_data.xpath(self.QUADRANT.format(pos="c"))[0].text
            return data_dict
        except IndexError:
            return {}


class DatastoreEntities(BaseEntitiesView):
    """
    represents central view where all QuadIcons, etc are displayed
    """
    @property
    def entity_class(self):
        return DatastoreEntity


class DatastoresView(BaseLoggedInPage):
    """
    represents whole All Datastores page
    """
    toolbar = View.nested(DatastoreToolBar)
    sidebar = View.nested(DatastoreSideBar)
    search = View.nested(Search)
    including_entities = View.include(DatastoreEntities, use_parent=True)

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                       'Datastores'] and
                self.entities.title.text == 'All Datastores')


class HostAllDatastoresView(DatastoresView):

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Hosts"] and
            self.entities.title.text == "{} (All Datastores)".format(self.context["object"].name)
        )


class ProviderAllDatastoresView(DatastoresView):
    """
    This view is used in test_provider_relationships
    """

    @property
    def is_displayed(self):
        msg = "{} (All Datastores)".format(self.context["object"].name)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Providers"] and
            self.entities.title.text == msg
        )


class DatastoreDetailsView(BaseLoggedInPage):
    """
    represents Datastore Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(DatastoreToolBar)
    sidebar = View.nested(DatastoreSideBar)

    @View.nested
    class entities(View):  # noqa
        """
        represents Details page when it is switched to Summary aka Tables view
        """
        properties = SummaryTable(title="Properties")
        registered_vms = SummaryTable(title="Information for Registered VMs")
        relationships = SummaryTable(title="Relationships")
        content = SummaryTable(title="Content")
        smart_management = SummaryTable(title="Smart Management")

    @property
    def is_displayed(self):
        return (super(BaseLoggedInPage, self).is_displayed and
                self.navigation.currently_selected == ['Compute', 'Infrastructure',
                                                       'Datastores'] and
                self.title.text == 'Datastore "{name}"'.format(name=self.context['object'].name))


class RegisteredHostsView(HostsView):
    """
    represents Hosts related to some datastore
    """
    @property
    def is_displayed(self):
        # todo: to define correct check
        return False


@attr.s
class Datastore(Pretty, BaseEntity, Taggable):
    """Model of an infrastructure datastore in cfme

    Args:
        name: Name of the datastore.
        provider: provider this datastore is attached to.

    """

    pretty_attrs = ['name', 'provider_key']
    _param_name = ParamClassName('name')
    name = attr.ib()
    provider = attr.ib()
    type = attr.ib(default=None)

    def __attrs_post_init__(self):
        # circular imports
        from cfme.infrastructure.host import HostsCollection
        self._collections = {'hosts': HostsCollection}

    @property
    def rest_api_entity(self):
        return self.appliance.rest_api.collections.data_stores.get(name=self.name)

    def delete(self, cancel=True):
        """
        Deletes a datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True

        Note:
            Datastore must have 0 hosts and 0 VMs for this to work.
        """
        # BZ 1467989 - this button is never getting enabled for some resources
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove Datastore from Inventory'
                                               if self.appliance.version >= '5.9'
                                               else 'Remove Datastore',
                                               handle_alert=(not cancel))
        view.flash.assert_success_message('Delete initiated for Datastore from the CFME Database')

    @property
    def hosts(self):
        return self.collections.hosts

    def get_hosts(self):
        """ Returns names of hosts (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no hosts found.
        """
        view = navigate_to(self, 'DetailsFromProvider')
        view.entities.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        return hosts_view.entities.get_all()

    def get_vms(self):
        """ Returns names of VMs (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no vms found.
        """
        view = navigate_to(self, 'Details')
        if 'VMs' in view.entities.relationships.fields:
            view.entities.relationships.click_at('VMs')
        else:
            view.entities.relationships.click_at('Managed VMs')
        # todo: to replace with correct view
        vms_view = view.browser.create_view(DatastoresView)
        return [vm.name for vm in vms_view.entities.get_all()]

    def delete_all_attached_vms(self):
        view = navigate_to(self, 'Details')
        view.entities.relationships.click_at('Managed VMs')
        # todo: to replace with correct view
        vms_view = view.browser.create_view(DatastoresView)
        for entity in vms_view.entities.get_all():
            entity.check()
        view.toolbar.configuration.item_select('Remove selected items from Inventory'
                                               if self.appliance.version >= '5.9'
                                               else 'Remove selected items',
                                               handle_alert=True)

        wait_for(lambda: bool(len(vms_view.entities.get_all())), fail_condition=True,
                 message="Wait datastore vms to disappear", num_sec=1000,
                 fail_func=self.browser.refresh)

    def delete_all_attached_hosts(self):
        view = navigate_to(self, 'Details')
        view.entities.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        for entity in hosts_view.entities.get_all():
            entity.check()
        view.toolbar.configuration.item_select('Remove items from Inventory'
                                               if self.appliance.version >= '5.9'
                                               else 'Remove items',
                                               handle_alert=True)

        wait_for(lambda: bool(len(hosts_view.entities.get_all())), fail_condition=True,
                 message="Wait datastore hosts to disappear", num_sec=1000,
                 fail_func=self.browser.refresh)

    @property
    def exists(self):
        try:
            view = navigate_to(self, 'Details')
            return view.is_displayed
        except ItemNotFound:
            return False

    @property
    def host_count(self):
        """ number of attached hosts.

        Returns:
            :py:class:`int` host count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Hosts'))

    @property
    def vm_count(self):
        """ number of attached VMs.

        Returns:
            :py:class:`int` vm count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Managed VMs'))

    def run_smartstate_analysis(self, wait_for_task_result=False):
        """ Runs smartstate analysis on this host

        Note:
            The host must have valid credentials already set up for this to work.
        """
        view = navigate_to(self, 'DetailsFromProvider')
        try:
            wait_for(lambda: view.toolbar.configuration.item_enabled('Perform SmartState Analysis'),
                     fail_condition=False, num_sec=10)
        except TimedOutError:
            raise MenuItemNotFound('Smart State analysis is disabled for this datastore')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_success_message(('"{}": scan successfully '
                                           'initiated'.format(self.name)))
        if wait_for_task_result:
            task = self.appliance.collections.tasks.instantiate(
                name="SmartState Analysis for [{}]".format(self.name), tab='MyOtherTasks')
            task.wait_for_finished()
            return task

    def wait_candu_data_available(self, timeout=900):
        """Waits until C&U data are available for this Datastore

        Args:
            timeout: Timeout passed to :py:func:`utils.wait.wait_for`
        """
        view = navigate_to(self, 'Details')
        wait_for(
            lambda: view.toolbar.monitoring.item_enabled("Utilization"),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=view.browser.refresh
        )


@attr.s
class DatastoreCollection(BaseCollection):
    """Collection class for :py:class:`cfme.infrastructure.datastore.Datastore`"""
    ENTITY = Datastore

    def all(self):
        "Returning all datastore objects with filtering support as per provider"
        provider = self.filters.get("provider")
        datastores = self.appliance.rest_api.collections.data_stores
        datastores = datastores.all_include_attributes(attributes=["hosts"])
        datastore_db = {ds.name: ds.hosts[0]["ems_id"] for ds in datastores}
        provider_db = {
            prov.id: get_crud_by_name(prov.name)
            for prov in self.appliance.rest_api.collections.providers.all
        }
        datastores = [
            self.instantiate(name=name, provider=provider_db[prov_id])
            for name, prov_id in datastore_db.items()
        ]
        return (
            [ds for ds in datastores if ds.provider.id == provider.id] if provider else datastores
        )

    def delete(self, *datastores):
        """
        Note:
            Datastores must have 0 hosts and 0 VMs for this to work.
        """
        datastores = list(datastores)
        checked_datastores = list()
        view = navigate_to(self, 'All')

        for datastore in datastores:
            try:
                view.entities.get_entity(name=datastore.name, surf_pages=True).check()
                checked_datastores.append(datastore)
            except ItemNotFound:
                raise ValueError('Could not find datastore {} in the UI'.format(datastore.name))

        if set(datastores) == set(checked_datastores):
            view.toolbar.configuration.item_select('Remove Datastores', handle_alert=True)
            view.flash.assert_success_message(
                'Delete initiated for Datastore from the CFME Database')

            for datastore in datastores:
                wait_for(lambda: not datastore.exists, num_sec=600, delay=30,
                         message='Wait for Datastore to be deleted')

    def run_smartstate_analysis(self, *datastores):
        datastores = list(datastores)

        checked_datastores = list()

        view = navigate_to(self, 'All')

        for datastore in datastores:
            try:
                view.entities.get_entity(name=datastore.name, surf_pages=True).check()
                checked_datastores.append(datastore)
            except ItemNotFound:
                raise ValueError('Could not find datastore {} in the UI'.format(datastore.name))

        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        for datastore in datastores:
            view.flash.assert_success_message(
                '"{}": scan successfully initiated'.format(datastore.name))


@navigator.register(DatastoreCollection, 'All')
class All(CFMENavigateStep):
    VIEW = DatastoresView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Datastores')

    def resetter(self):
        """
        resets page to default state when user navigates to All Datastores destination
        """
        # Reset view and selection
        self.view.sidebar.datastores.tree.click_path('All Datastores')
        tb = self.view.toolbar
        if tb.view_selector.is_displayed and 'Grid View' not in tb.view_selector.selected:
            tb.view_selector.select("Grid View")
        self.view.entities.paginator.reset_selection()


@navigator.register(Datastore, 'Details')
class Details(CFMENavigateStep):
    VIEW = DatastoreDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Datastore, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DatastoreDetailsView

    def prerequisite(self):
        prov_view = navigate_to(self.obj.provider, 'Details')
        prov_view.entities.summary('Relationships').click_at('Datastores')
        return self.obj.create_view(DatastoresView)

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Datastore, "Utilization")
class Utilization(CFMENavigateStep):
    VIEW = DatastoreInfraUtilizationView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select("Utilization")
