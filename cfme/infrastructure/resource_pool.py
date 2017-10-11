""" A model of an Infrastructure Resource pool in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Resource pool pages.
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Button, Dropdown, FlashMessages

from cfme.base.ui import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.exceptions import ResourcePoolNotFound
from cfme.web_ui import match_location
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud
from cfme.utils.wait import wait_for
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, ManageIQTree, PaginationPane, Text, Table, Search, BreadCrumb,
    SummaryTable, Accordion)


class ResourcePoolToolbar(View):
    """The toolbar on the main page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ResourcePoolDetailsToolbar(View):
    """The toolbar on the details page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button(title='Download summary in PDF format')


class ResourcePoolDetailsAccordion(View):
    """The accordian on the details page"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class ResourcePoolEntities(View):
    """Entities on the main list page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ResourcePoolDetailsEntities(View):
    """Entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')


class ResourcePoolView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_resource_pool(self):
        nav_chain = ['Compute', 'Infrastructure', 'Resource Pools']
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == nav_chain and
            # TODO: Also needs to be converted to Widgetastic
            match_location(controller='resource_pool', title='Resource Pools'))


class ResourcePoolAllView(ResourcePoolView):
    """The "all" view -- a list of app the resource pools"""
    @property
    def is_displayed(self):
        return (
            self.in_resource_pool and
            self.entities.title.text == 'Resource Pools')

    toolbar = View.nested(ResourcePoolToolbar)
    entities = View.nested(ResourcePoolEntities)
    paginator = PaginationPane()


class ResourcePoolDetailsView(ResourcePoolView):
    """The details page of a resource pool"""
    @property
    def is_displayed(self):
        """Is this page being displayed?"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_resource_pool and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ResourcePoolDetailsToolbar)
    sidebar = View.nested(ResourcePoolDetailsAccordion)
    entities = View.nested(ResourcePoolDetailsEntities)


class ResourcePool(Pretty, Navigatable, WidgetasticTaggable):
    """ Model of an infrastructure Resource pool in cfme

    Args:
        name: Name of the Resource pool.
        provider_key: Name of the provider this resource pool is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Resourcepool``.
    """
    pretty_attrs = ['name', 'provider_key']

    def __init__(self, name=None, provider_key=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.quad_name = 'resource_pool'
        self.name = name
        if provider_key:
            self.provider = get_crud(provider_key, appliance=appliance)
        else:
            self.provider = None

    def _get_context(self):
        context = {'resource_pool': self}
        if self.provider:
            context['provider'] = self.provider
        return context

    def delete(self, cancel=True, wait=False):
        """Deletes a resource pool from CFME

        :param cancel: Whether or not to cancel the deletion, defaults to True
        :param wait: Whether or not to wait for the delete, defaults to False
        """
        view = navigate_to(self, 'Details')
        item_name = 'Remove Resource Pool'
        view.toolbar.configuration.item_select(item_name, handle_alert=not cancel)

        # cancel doesn't redirect, confirmation does
        view.flush_widget_cache()
        if cancel:
            view = self.create_view(ResourcePoolDetailsView)
        else:
            view = self.create_view(ResourcePoolAllView)
        wait_for(lambda: view.is_displayed, fail_condition=False, num_sec=10, delay=1)

        # flash message only displayed if it was deleted
        if not cancel:
            msg = 'The selected Resource Pools was deleted'
            view.entities.flash.assert_success_message(msg)

        if wait:
            def refresh():
                if self.provider:
                    self.provider.refresh_provider_relationships()
                view.browser.selenium.refresh()
                view.flush_widget_cache()

            wait_for(lambda: not self.exists, fail_condition=False, fail_func=refresh, num_sec=500,
                     message='Wait for resource pool to be deleted')

    def wait_for_exists(self):
        """Wait for the resource pool to be created"""
        view = navigate_to(self, 'All')

        def refresh():
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.selenium.refresh()
            view.flush_widget_cache()

        wait_for(lambda: self.exists, fail_condition=False, num_sec=1000, fail_func=refresh,
                 message='Wait resource pool to appear')

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific resource pool.

        Args:
            ident: An InfoBlock title, followed by the Key name, e.g. "Properties"
        Returns:
            returns: A string representing the contents of the InfoBlock's value.
        """
        view = navigate_to(self, 'Details')
        table = None
        if ident[0] == 'Properties':
            table = view.properties
        elif ident[0] == 'Relationships':
            table = view.relationships
        elif ident[0] == 'Smart Management':
            table = view.smart_management
        if table:
            return table.get_text_of(ident[1])
        return None

    @property
    def exists(self):
        view = navigate_to(self, 'All')
        try:
            view.toolbar.view_selector.select('List View')
            view.paginator.find_row_on_pages(view.entities.table, name=self.name)
            return True
        except NoSuchElementException:
            return False


@navigator.register(ResourcePool, 'All')
class All(CFMENavigateStep):
    """A navigation step for the All page"""
    VIEW = ResourcePoolAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Resource Pools')

    def resetter(self):
        """Reset view and selection"""
        self.view.toolbar.view_selector.select('Grid View')
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(ResourcePool, 'Details')
class Details(CFMENavigateStep):
    """A navigation step for the Details page"""
    VIEW = ResourcePoolDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        """Navigate to the item"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name
            )
        except NoSuchElementException:
            raise ResourcePoolNotFound('Resource pool {} not found'.format(self.obj.name))
        row.click()
