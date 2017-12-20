""" Page functions for Tenant pages
"""
import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import VersionPick
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav, Button, Dropdown, Input

from cfme.base.ui import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.exceptions import TenantNotFound, DestinationNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.log import logger
from cfme.utils.version import Version
from cfme.utils.wait import wait_for, TimedOutError
from widgetastic_manageiq import (
    Accordion, BootstrapSelect, BreadCrumb, ItemsToolBarViewSelector, PaginationPane,
    SummaryTable, Table, Text, BaseNonInteractiveEntitiesView, BaseEntitiesView)


class TenantToolbar(View):
    """The toolbar on the tenants page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class TenantDetailsToolbar(View):
    """The toolbar on the tenant details page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Button('Download summary in PDF format')


class TenantDetailsAccordion(View):
    """The accordion on the details page"""
    @View.nested
    class properties(Accordion):        # noqa
        nav = BootstrapNav('//div[@id="ems_prop"]//ul')

    @View.nested
    class relationships(Accordion):     # noqa
        nav = BootstrapNav('//div[@id="ems_rel"]//ul')


class TenantEntities(BaseEntitiesView):
    """The entities on the main list page"""
    table = Table('//div[@id="gtl_div"]//table')
    # todo: remove stuff about and use the same widgets from entities view ^^


class TenantDetailsEntities(View):
    """The entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    relationships = SummaryTable(title='Relationships')
    quotas = SummaryTable(title='Quotas')
    smart_management = SummaryTable(title='Smart Management')


class TenantEditEntities(View):
    """The entities on the add/edit page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class TenantEditTagEntities(View):
    """The entities on the edit tags page"""
    breadcrumb = BreadCrumb()
    title = Text('#explorer_title_text')
    included_widgets = View.include(BaseNonInteractiveEntitiesView, use_parent=True)


class TenantView(BaseLoggedInPage):
    """A base view for all the Tenant pages"""
    @property
    def in_tenants(self):
        """Determine if the Tenants page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Tenants']
        )


class TenantAllView(TenantView):
    """The all tenants page"""
    toolbar = View.nested(TenantToolbar)
    including_entities = View.include(TenantEntities, use_parent=True)
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        """This is page currently being displayed"""
        return self.in_tenants and self.entities.title.text == 'Cloud Tenants'


class TenantDetailsView(TenantView):
    """The details page for a tenant"""
    toolbar = View.nested(TenantDetailsToolbar)
    sidebar = View.nested(TenantDetailsAccordion)
    entities = View.nested(TenantDetailsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_tenants and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class TenantAddForm(View):
    """The form on the Add page"""
    cloud_provider = BootstrapSelect(id='ems_id')
    name = Input('name')
    save_button = VersionPick({
        Version.lowest(): Button('Save'),
        '5.9': Button('Add')
    })
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')


class TenantAddView(TenantView):
    """The add page for tenants"""
    entities = View.nested(TenantEditEntities)
    form = View.nested(TenantAddForm)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = 'Add New Cloud Tenant'
        return (
            self.in_tenants and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class TenantEditForm(View):
    """The form on the Edit page"""
    name = Input('name')
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')


class TenantEditView(TenantView):
    """The edit page for tenants"""
    entities = View.nested(TenantEditEntities)
    form = View.nested(TenantEditForm)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = 'Edit Cloud Tenant "{}"'.format(self.context['object'].name)
        return (
            self.in_tenants and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


@attr.s
class Tenant(BaseEntity, WidgetasticTaggable):
    """Tenant Class

    """
    _param_name = 'Tenant'

    name = attr.ib()
    provider = attr.ib()

    def wait_for_disappear(self, timeout=300):
        self.provider.refresh_provider_relationships()
        try:
            return wait_for(lambda: self.exists,
                            fail_condition=True,
                            timeout=timeout,
                            message='Wait for cloud tenant to disappear',
                            delay=10,
                            fail_func=self.browser.refresh)
        except TimedOutError:
            logger.error('Timed out waiting for tenant to disappear, continuing')

    def wait_for_appear(self, timeout=600):
        self.provider.refresh_provider_relationships()
        return wait_for(lambda: self.exists, timeout=timeout, delay=10,
                        message='Wait for cloud tenant to appear', fail_func=self.browser.refresh)

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        updated_name = updates.get('name', self.name + '_edited')
        view.form.fill({'name': updated_name})
        view.form.save_button.click()
        self.provider.refresh_provider_relationships()
        return wait_for(lambda: self.exists, fail_condition=False, timeout=600,
                        message='Wait for cloud tenant to appear', delay=10,
                        fail_func=self.browser.refresh)

    def delete(self, wait=True):
        """Delete the tenant"""

        try:
            view = navigate_to(self, 'Details')
        except NoSuchElementException as ex:
            # Catch general navigation exceptions and raise
            raise TenantNotFound(
                'Exception while navigating to Tenant details: {}'.format(ex))
        view.toolbar.configuration.item_select('Delete Cloud Tenant')

        result = view.flash.assert_success_message(
            'Delete initiated for 1 Cloud Tenant.')
        if wait:
            self.provider.refresh_provider_relationships()
            result = self.wait_for_disappear(600)
        return result

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except NoSuchElementException:
            return False
        else:
            return True


@attr.s
class TenantCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.cloud.tenant.Tenant`."""

    ENTITY = Tenant

    def create(self, name, provider, wait=True):
        """Add a cloud Tenant from the UI and return the Tenant object"""
        page = navigate_to(self, 'Add')
        changed = page.form.fill({
            'cloud_provider': provider.name,
            'name': name
        })
        if changed:
            page.form.save_button.click()
        else:
            page.form.cancel_button.click()

        all_view = self.create_view(TenantAllView)
        wait_for(lambda: all_view.is_displayed, num_sec=120, delay=3,
                 fail_func=all_view.flush_widget_cache, handle_exception=True)

        if not changed:
            if self.appliance.version >= '5.8':
                msg = 'Add of Cloud Tenant was cancelled by the user'
            else:
                msg = 'Add of new Cloud Tenant was cancelled by the user'
            all_view.flash.assert_success_message(msg)
        else:
            all_view.flash.assert_success_message(
                'Cloud Tenant "{}" created'.format(name))

        tenant = self.instantiate(name, provider)

        if wait:
            def refresh():
                """Refresh a few things"""
                tenant.provider.refresh_provider_relationships()
                all_view.flush_widget_cache()
                self.browser.refresh()

            wait_for(lambda: tenant.exists, timeout=600,
                     message='Wait for cloud tenant to appear',
                     delay=10, fail_func=refresh)

        return tenant

    def delete(self, *tenants):
        """Delete one or more  Tenants from the list of the Tenants

        Args:
            list of the `cfme.cloud.tenant.Tenant` objects
        """

        tenants = list(tenants)
        checked_tenants = []
        view = navigate_to(self, 'All')
        # double check we're in List View
        view.toolbar.view_selector.select('List View')
        if not view.table.is_displayed:
            raise ValueError('No Tenants found')
        for row in view.table:
            for tenant in tenants:
                if tenant.name == row.name.text:
                    checked_tenants.append(tenant)
                    row[0].check()
                    break
            if set(tenants) == set(checked_tenants):
                break
        if set(tenants) != set(checked_tenants):
            raise ValueError('Some tenants were not found in the UI')
        view.toolbar.configuration.item_select('Delete Cloud Tenants', handle_alert=True)
        for tenant in tenants:
            tenant.wait_for_disappear()
        view.flash.assert_no_error()

        # TODO: Assert deletion flash message for selected tenants
        # it is not shown in current UI, so not asserting


@navigator.register(TenantCollection, 'All')
class TenantAll(CFMENavigateStep):
    VIEW = TenantAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Go to the All page"""
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Tenants')

    def resetter(self):
        """Reset the view"""
        self.view.toolbar.view_selector.select('List View')
        self.view.paginator.reset_selection()


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    VIEW = TenantDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        """Navigate to the details page"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.paginator.find_row_on_pages(
            self.prerequisite_view.table, name=self.obj.name)
        row.click()

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(TenantCollection, 'Add')
class TenantAdd(CFMENavigateStep):
    VIEW = TenantAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        """Navigate to the Add page"""
        if self.obj.appliance.version >= '5.7':
            self.prerequisite_view.toolbar.configuration.item_select('Create Cloud Tenant')
        else:
            raise DestinationNotFound('Cannot add Cloud Tenants in CFME < 5.7')


@navigator.register(Tenant, 'Edit')
class TenantEdit(CFMENavigateStep):
    VIEW = TenantEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the edit page"""
        if self.obj.appliance.version >= '5.7':
            self.prerequisite_view.toolbar.configuration.item_select('Edit Cloud Tenant')
        else:
            raise DestinationNotFound('Cannot edit Cloud Tenants in CFME < 5.7')
