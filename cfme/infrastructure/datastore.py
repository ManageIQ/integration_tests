""" A model of an Infrastructure Datastore in CFME
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View, Text
from widgetastic_manageiq import (ManageIQTree, SummaryTable, ItemsToolBarViewSelector,
                                  BaseEntitiesView)
from widgetastic_patternfly import Dropdown, Accordion, FlashMessages

from cfme.base.login import BaseLoggedInPage
from cfme.common.host_views import HostsView
from cfme.utils.appliance import Navigatable
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


class DatastoreEntities(BaseEntitiesView):
    """
    represents central view where all QuadIcons, etc are displayed
    """
    pass


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
    class contents(View):  # noqa
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


class Datastore(Pretty, Navigatable):
    """ Model of an infrastructure datastore in cfme

    Args:
        name: Name of the datastore.
        provider: provider this datastore is attached to.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name, provider, type=None, appliance=None):
        Navigatable.__init__(self, appliance)
        self.name = name
        self.type = type
        self.provider = provider

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
        view.contents.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        return [h.name for h in hosts_view.entities.get_all()]

    def get_vms(self):
        """ Returns names of VMs (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no vms found.
        """
        view = navigate_to(self, 'Details')
        if 'VMs' in view.contents.relationships.fields:
            view.contents.relationships.click_at('VMs')
        else:
            view.contents.relationships.click_at('Managed VMs')
        # todo: to replace with correct view
        vms_view = view.browser.create_view(DatastoresView)
        return [vm.name for vm in vms_view.entities.get_all()]

    def delete_all_attached_vms(self):
        view = navigate_to(self, 'Details')
        view.contents.relationships.click_at('Managed VMs')
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
        view.contents.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        for entity in hosts_view.entities.get_all():
            entity.check()
        view.toolbar.configuration.item_select("Remove items", handle_alert=True)
        wait_for(lambda: bool(len(hosts_view.entities.get_all())), fail_condition=True,
                 message="Wait datastore hosts to disappear", num_sec=1000,
                 fail_func=self.browser.refresh)

    @property
    def exists(self):
        view = navigate_to(self, 'Details')
        return view.is_displayed

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


@navigator.register(Datastore, 'All')
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
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_first_entity(by_name=self.obj.name).click()


@navigator.register(Datastore, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DatastoreDetailsView

    def step(self):
        prov_view = navigate_to(self.obj.provider, 'Details')
        prov_view.contents.relationships.click_at('Datastores')


def get_all_datastores():
    """Returns names (from quadicons) of all datastores"""
    view = navigate_to(Datastore, 'All')
    return [ds.name for ds in view.entities.get_all()]
