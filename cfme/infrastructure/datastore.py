""" A model of an Infrastructure Datastore in CFME
"""
import attr

from navmazing import NavigateToAttribute
from widgetastic.widget import View, Text
from cfme.exceptions import ItemNotFound
from widgetastic_manageiq import (ManageIQTree,
                                  SummaryTable,
                                  ItemsToolBarViewSelector,
                                  BaseEntitiesView,
                                  NonJSBaseEntity,
                                  BaseListEntity,
                                  BaseQuadIconEntity,
                                  BaseTileIconEntity,
                                  JSBaseEntity)
from widgetastic.widget import ParametrizedView
from widgetastic_patternfly import Dropdown, Accordion, FlashMessages
from widgetastic.utils import Version, VersionPick
from cfme.base.login import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.common.host_views import HostsView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for


class DatastoreToolBar(View):
    """
    represents datastore toolbar and its controls
    """
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
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
        return {
            'type': self.browser.get_attribute("alt", self.QUADRANT.format(pos="a")),
            'no_vm': int(self.browser.text(self.QUADRANT.format(pos="b"))),
            'no_host': int(self.browser.text(self.QUADRANT.format(pos="c"))),
        }


class DatastoreTileIconEntity(BaseTileIconEntity):
    quad_icon = ParametrizedView.nested(DatastoreQuadIconEntity)


class DatastoreListEntity(BaseListEntity):
    pass


class NonJSDatastoreEntity(NonJSBaseEntity):
    quad_entity = DatastoreQuadIconEntity
    list_entity = DatastoreListEntity
    tile_entity = DatastoreTileIconEntity


def DatastoreEntity():  # noqa
    """Temporary wrapper for Datastore Entity during transition to JS based Entity """
    return VersionPick({
        Version.lowest(): NonJSDatastoreEntity,
        '5.9': JSBaseEntity,
    })


class DatastoreEntities(BaseEntitiesView):
    """
    represents central view where all QuadIcons, etc are displayed
    """

    @property
    def entity_class(self):
        return DatastoreEntity().pick(self.browser.product_version)


class DatastoresView(BaseLoggedInPage):
    """
    represents whole All Datastores page
    """
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(DatastoreToolBar)
    sidebar = View.nested(DatastoreSideBar)
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


class DatastoreDetailsView(BaseLoggedInPage):
    """
    represents Datastore Details page
    """
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
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
class Datastore(Pretty, BaseEntity, WidgetasticTaggable):
    """ Model of an infrastructure datastore in cfme

    Args:
        name: Name of the datastore.
        provider: provider this datastore is attached to.
    """

    pretty_attrs = ['name', 'provider_key']

    name = attr.ib()
    provider = attr.ib()
    type = attr.ib(default=None)

    def delete(self, cancel=True):
        """
        Deletes a datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True

        Note:
            Datastore must have 0 hosts and 0 VMs for this to work.
        """
        # BZ 1467989 - this button is never getting enabled
        view = navigate_to(self, 'Details')
        wait_for(lambda: view.toolbar.configuration.item_enabled('Remove Datastore'),
                 fail_condition=False, num_sec=10)
        view.toolbar.configuration.item_select('Remove Datastore', handle_alert=not cancel)
        view.flash.assert_success_message('Delete initiated for Datastore from the CFME Database')

    def get_hosts(self):
        """ Returns names of hosts (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no hosts found.
        """
        view = navigate_to(self, 'Details')
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
        view.toolbar.configuration.item_select("Remove selected items", handle_alert=True)
        wait_for(lambda: bool(len(vms_view.entities.get_all())), fail_condition=True,
                 message="Wait datastore vms to disappear", num_sec=1000,
                 fail_func=self.browser.refresh)

    def delete_all_attached_hosts(self):
        view = navigate_to(self, 'Details')
        view.entities.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        for entity in hosts_view.entities.get_all():
            entity.check()
        view.toolbar.configuration.item_select("Remove items", handle_alert=True)
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

    def run_smartstate_analysis(self):
        """ Runs smartstate analysis on this host

        Note:
            The host must have valid credentials already set up for this to work.
        """
        view = navigate_to(self, 'Details')
        wait_for(lambda: view.toolbar.configuration.item_enabled('Perform SmartState Analysis'),
                 fail_condition=False, num_sec=10)
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_success_message(('"{}": scan successfully '
                                           'initiated'.format(self.name)))


@attr.s
class DatastoreCollection(BaseCollection):
    """Collection class for `cfme.infrastructure.datastore.Datastore`"""
    ENTITY = Datastore

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
                view.entities.get_entity(by_name=datastore.name, surf_pages=True).check()
                checked_datastores.append(datastore)
            except ItemNotFound:
                raise ValueError('Could not find datastore {} in the UI'.format(datastore.name))

        if set(datastores) == set(checked_datastores):
            view.toolbar.configuration.item_select('Remove Datastores', handle_alert=True)
            view.entities.flash.assert_success_message(
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
                view.entities.get_entity(by_name=datastore.name, surf_pages=True).check()
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
        paginator = self.view.entities.paginator
        if paginator.exists:
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(Datastore, 'Details')
class Details(CFMENavigateStep):
    VIEW = DatastoreDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).click()


@navigator.register(Datastore, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DatastoreDetailsView

    def step(self):
        prov_view = navigate_to(self.obj.provider, 'Details')
        prov_view.entities.relationships.click_at('Datastores')


def get_all_datastores():
    """Returns names (from quadicons) of all datastores"""
    view = navigate_to(Datastore, 'All')
    return [ds.name for ds in view.entities.get_all()]
