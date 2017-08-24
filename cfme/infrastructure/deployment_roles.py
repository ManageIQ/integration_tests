""" A model of an Infrastructure Deployment roles in CFME"""

from functools import partial
from navmazing import NavigateToSibling, NavigateToAttribute, NavigateToObject
from widgetastic.exceptions import NoSuchElementException
from cfme.exceptions import RoleNotFound
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav, Button, Dropdown, FlashMessages
from widgetastic_manageiq import (
    Accordion, BootstrapSelect, BreadCrumb, ItemsToolBarViewSelector, PaginationPane,
    SummaryTable, Table, Text, BootstrapTreeview)

from cfme.base.ui import BaseLoggedInPage
from cfme.web_ui import match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.log import logger
from utils.wait import wait_for, TimedOutError
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.common.provider_views import InfraProviderDetailsView


class DeploymentRoleToolbar(View):
    """The toolbar on the Deployment Role page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class DeploymentRoleDetailsToolbar(View):
    """The toolbar on the Deployment Role details page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button('Download summary in PDF format')


class DeploymentRoleComparisonToolbar(View):
    """ The toolbar on Comparison Page of roles"""
    all_attributes = Button(title="All attributes")
    different_values_attributes = Button(title="Attributes with different values")
    same_values_attributes = Button(title="Attributes with same values")

    details_mode = Button(title="Details Mode")
    exists_mode = Button(title="Exists Mode")
    download = Dropdown('Download')


class DeploymentRoleDetailsAccordion(View):
    """The accordion on the Deployment Role details page"""
    @View.nested
    class properties(Accordion):        # noqa
        nav = BootstrapNav('//div[@id="ems_prop"]//ul')

    @View.nested
    class relationships(Accordion):     # noqa
        nav = BootstrapNav('//div[@id="ems_rel"]//ul')


class DeploymentRoleEntities(View):
    """The entities on the main list Deployment Role page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class DeploymentRoleDetailsEntities(View):
    """The entities on the Deployment Role details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    relationships = SummaryTable(title='Relationships')
    total_for_node = SummaryTable(title='Totals for Nodes')
    total_for_vm = SummaryTable(title='Totals for VMs')
    smart_management = SummaryTable(title='Smart Management')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class DeploymentRoleComparisonEntities(View):
    """The entities on compare Deployment role page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//*[@id="compare-grid"]/table')


class DeploymentRoleView(BaseLoggedInPage):
    """A base view for all the Deployment Role pages"""
    @property
    def in_dep_role(self):
        """Determine if the Deployment page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Deployment Roles'] and
            match_location(controller='ems_cluster', title='Deployment Roles'))


class DeploymentRoleAllView(DeploymentRoleView):
    """The all Deployment Role page"""
    toolbar = View.nested(DeploymentRoleToolbar)
    entities = View.nested(DeploymentRoleEntities)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        """This is page currently being displayed"""
        return (
            self.in_dep_role and
            (self.entities.title.text == 'Deployment Roles' or
             self.entities.title.text == 'All Cluster / Deployment Role'))


class DeploymentRoleAllForProviderView(DeploymentRoleView):
    """The Deployment Role for Prover page"""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(DeploymentRoleToolbar)
    sidebar = View.nested(DeploymentRoleDetailsAccordion)
    entities = View.nested(DeploymentRoleEntities)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        import pdb
        pdb.set_trace()
        expected_title = '{} (All Deployment Roles)'.format(self.context['object'].provider.name)

        return (
            self.logged_in_as_current_user and
            self.entities.breadcrumb.active_location == expected_title)


class DeploymentRoleDetailsView(DeploymentRoleView):
    """The details page for a Deployment Roles"""
    toolbar = View.nested(DeploymentRoleDetailsToolbar)
    sidebar = View.nested(DeploymentRoleDetailsAccordion)
    entities = View.nested(DeploymentRoleDetailsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_dep_role and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class DeploymentRoleEditTagsView(DeploymentRoleView):
    """The edit tags of Deployment Role"""
    breadcrumb = BreadCrumb()
    title = Text('#explorer_title_text')
    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_dep_role and
            self.breadcrumb.active_location == 'Tag Assignment')


class DeploymentRoleManagePoliciesView(DeploymentRoleView):
    """Deployment role Manage Policies view."""
    breadcrumb = BreadCrumb()
    policies = BootstrapTreeview("protectbox")
    save_button = Button("Save")
    reset_button = Button("Reset")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        """Is this page currently displayed"""
        return (
            self.in_dep_role and
            (self.breadcrumb.active_location == "'Cluster / Deployment Role' Policy Assignment" or
             self.breadcrumb.active_location == "'Deployment Role' Policy Assignment")
        )


class DeploymentRoles(Navigatable):
    """ Model of an infrastructure deployment roles in cfme

    Args:
        name: Name of the role.
        provider: provider this role is attached to
            (deployment roles available only for Openstack!).
    """

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider

        if not isinstance(provider, OpenstackInfraProvider):
            raise NotImplementedError('Deployment roles available only '
                                      'for Openstack provider')
        Navigatable.__init__(self, appliance=appliance)

    def delete(self, cancel=False):
        """Returning bool value for deletion"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove item',
                                               handle_alert=not cancel)

        # cancel doesn't redirect, confirmation does
        if cancel:
            view = self.create_view(DeploymentRoleDetailsView)

        else:
            view = self.create_view(DeploymentRoleAllView)
            try:
                wait_for(lambda: view.paginator.find_row_on_pages(view.entities.table,
                                                                  name=self.name).is_displayed,
                         fail_condition=True,
                         timeout=300,
                         message='Wait for Role to disappear',
                         delay=10,
                         fail_func=self.browser.refresh)
            except TimedOutError:
                logger.error('Timed out waiting for Role to disappear, continuing')
                return False
            except NoSuchElementException:
                return True


@navigator.register(DeploymentRoles, 'All')
class All(CFMENavigateStep):

    VIEW = DeploymentRoleAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        nav_select = partial(self.prerequisite_view.navigation.select, 'Compute', 'Infrastructure')
        try:
            nav_select('Deployment Roles')
        except NoSuchElementException:
            nav_select('Clusters / Deployment Roles')

    def resetter(self):
        """Reset the view"""
        self.view.toolbar.view_selector.select('List View')
        if self.view.entities.table.is_displayed:
            self.view.paginator.check_all()
            self.view.paginator.uncheck_all()


@navigator.register(DeploymentRoles, 'Details')
class Details(CFMENavigateStep):
    VIEW = DeploymentRoleDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        """Navigate to the details page of Role"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table, name=self.obj.name)
            row.click()
        except NoSuchElementException:
            raise RoleNotFound("Deployment Role {} not found".format(self.obj.name))

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(DeploymentRoles, 'ProviderDetails')
class ProviderDetails(CFMENavigateStep):
    VIEW = InfraProviderDetailsView
    prerequisite = NavigateToObject(OpenstackInfraProvider, 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.provider.name).click()

    def resetter(self):
        self.view.toolbar.view_selector.summary_button.click()


@navigator.register(DeploymentRoles, 'AllForProvider')
class AllForProvider(CFMENavigateStep):
    VIEW = DeploymentRoleAllForProviderView
    prerequisite = NavigateToSibling('ProviderDetails')

    def step(self):
        try:
            self.prerequisite_view.contents.relationships.click_at('Deployment Roles')
        except NameError:
            self.prerequisite_view.contents.relationships.click_at('Clusters / Deployment Roles')


@navigator.register(DeploymentRoles, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DeploymentRoleDetailsView
    prerequisite = NavigateToSibling('AllForProvider')

    def step(self):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table, name=self.obj.name)
            row.click()
        except NoSuchElementException:
            raise RoleNotFound("Deployment Role {} not found".format(self.obj.name))
