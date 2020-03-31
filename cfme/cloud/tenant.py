""" Page functions for Tenant pages
"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base.ui import BaseLoggedInPage
from cfme.common import Taggable
from cfme.exceptions import DestinationNotFound
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.networks import ValidateStatsMixin
from cfme.networks.network_router import NetworkRouterCollection
from cfme.networks.subnet import SubnetCollection
from cfme.networks.views import NetworkEntitySubnetView
from cfme.networks.views import OneTenantNetworkRouterView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BaseNonInteractiveEntitiesView
from widgetastic_manageiq import BootstrapSelect
from widgetastic_manageiq import DetailsToolBarViewSelector
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table
from widgetastic_manageiq import Text


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
    download = Button('Print or export summary')


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
    # TODO: remove stuff about and use the same widgets from entities view ^^


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
    search = View.nested(Search)

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()

    @property
    def is_displayed(self):
        """This is page currently being displayed"""
        return self.in_tenants and self.entities.title.text == 'Cloud Tenants'


class ProviderTenantAllView(TenantAllView):

    @property
    def is_displayed(self):
        def get_provider_navigation(provider):
            # Return navigation path based on a type of a provider
            # TODO: Store navigation target as class attribute in Provider classes
            if getattr(provider, 'name', False) and provider.category == 'cloud':
                return ['Compute', 'Clouds', 'Providers']
            elif getattr(provider, 'name', False) and provider.category == 'networks':
                return ['Networks', 'Providers']
            return []

        expected_title = '{} (All Cloud Tenants)'
        obj = self.context['object']
        is_entity = getattr(obj, 'name', False) and isinstance(obj, BaseEntity)
        is_filtered = isinstance(obj, BaseCollection) and obj.filters
        provider = obj.filters.get('parent') or obj.filters.get('provider') if is_filtered else None

        if is_entity:
            logger.debug('Tenant view context object is assumed to be provider: %r', obj)
            matched_title = self.entities.title.text == expected_title.format(obj.name)
            matched_navigation = self.navigation.currently_selected == get_provider_navigation(obj)
        elif provider and hasattr(provider, 'name'):
            # filtered collection, use provider object's name and provider object's navigation
            logger.debug(
                'Tenant view context object has provider related to view with name attribute: %r',
                obj.filters
            )
            matched_title = self.entities.title.text == expected_title.format(provider.name)
            matched_navigation = (
                self.navigation.currently_selected == get_provider_navigation(provider)
            )
        else:
            # not an entity with a name, or a filtered collection
            matched_title = False
            matched_navigation = False

        return self.logged_in_as_current_user and matched_navigation and matched_title


class TenantDetailsView(TenantView):
    """The details page for a tenant"""
    toolbar = View.nested(TenantDetailsToolbar)
    sidebar = View.nested(TenantDetailsAccordion)
    entities = View.nested(TenantDetailsEntities)

    view_selector = View.nested(DetailsToolBarViewSelector)

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
    save_button = Button('Add')
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
class Tenant(BaseEntity, Taggable, ValidateStatsMixin):
    """Tenant Class

    """
    string_name = 'Tenant'
    _param_name = 'Tenant'

    _collections = {
        'subnets': SubnetCollection,
        'routers': NetworkRouterCollection
    }

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
            raise ItemNotFound(
                f'Exception while navigating to Tenant details: {ex}')
        view.toolbar.configuration.item_select('Delete Cloud Tenant')

        result = view.flash.assert_success_message(
            'Delete initiated for 1 Cloud Tenant.')
        if wait:
            self.provider.refresh_provider_relationships()
            result = self.wait_for_disappear(600)
        return result


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

        all_view = self.create_view(TenantAllView, wait="20s")

        if not changed:
            all_view.flash.assert_success_message("Add of Cloud Tenant was cancelled by the user")
        else:
            all_view.flash.assert_success_message(
                f'Cloud Tenant "{name}" created')

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

    def all(self):
        provider = self.filters.get('provider')  # None if no filter, need for entity instantiation
        view = navigate_to(self, 'All')
        result = []
        for _ in view.entities.paginator.pages():
            tenants = view.entities.get_all()
            for tenant in tenants:
                if provider is not None:
                    if tenant.data['cloud_provider'] == provider.name:
                        entity = self.instantiate(tenant.data['name'], provider)
                else:
                    entity = self.instantiate(tenant.data['name'],
                                              get_crud_by_name(tenant.data['cloud_provider']))
                result.append(entity)
        return result


@navigator.register(TenantCollection, 'All')
class TenantAll(CFMENavigateStep):
    VIEW = TenantAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Go to the All page"""
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Tenants')

    def resetter(self, *args, **kwargs):
        """Reset the view"""
        self.view.toolbar.view_selector.select('List View')
        self.view.paginator.reset_selection()


@navigator.register(Tenant, 'Details')
class TenantDetails(CFMENavigateStep):
    VIEW = TenantDetailsView

    def prerequisite(self, *args, **kwargs):
        """
        Navigate through provider or collection filter if it exists else navigate through collection
        object """
        # Here we assume that every tenant has a parent collection
        filter = self.obj.provider or self.obj.parent.filters.get('parent')
        if filter:
            return navigate_to(filter, 'CloudTenants')
        else:
            return navigate_to(self.obj.parent, 'All')

    def step(self, *args, **kwargs):
        """Navigate to the details page"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.paginator.find_row_on_pages(
            self.prerequisite_view.table, name=self.obj.name)
        row.click()
        if self.appliance.version > "5.11":
            # in 5.11 TenantDetailsView has a dashboard view (5.10 doesn't) and it breaks navigation
            self.view.view_selector.select("Summary View")

    def resetter(self, *args, **kwargs):
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


@navigator.register(Tenant, 'CloudSubnets')
class CloudSubnets(CFMENavigateStep):
    VIEW = NetworkEntitySubnetView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        item = 'Cloud Subnets'
        if not int(self.prerequisite_view.entities.relationships.get_text_of(item)):
            raise DestinationNotFound(
                f'Cloud Tenant {self.obj} has a 0 count for {item} relationships')

        self.prerequisite_view.entities.relationships.click_at(item)


@navigator.register(Tenant, 'NetworkRouters')
class NetworkRouters(CFMENavigateStep):
    VIEW = OneTenantNetworkRouterView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        item = 'Network Routers'
        if not int(self.prerequisite_view.entities.relationships.get_text_of(item)):
            raise DestinationNotFound(
                f'Cloud Tenant {self.obj} has a 0 count for {item} relationships')

        self.prerequisite_view.entities.relationships.click_at(item)
