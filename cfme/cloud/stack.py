import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View
from widgetastic_patternfly import Button, Dropdown, BootstrapNav

from cfme.base.ui import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.exceptions import CandidateNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (
    Accordion, BreadCrumb, ItemsToolBarViewSelector, PaginationPane,
    SummaryTable, Table, Text, BaseEntitiesView)


class StackToolbar(View):
    """The toolbar on the stacks page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class StackDetailsToolbar(View):
    """The toolbar on the stacks detail page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')
    download = Button('Download summary in PDF format')


class StackSubpageToolbar(View):
    """The toolbar on the sub pages, like resources and security groups"""
    show_summary = Button('Show {} Summary')      # TODO How to get name in there?
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    lifecycle = Dropdown('Lifecycle')


class StackDetailsAccordion(View):
    """The accordion on the details page"""
    @View.nested
    class properties(Accordion):        # noqa
        nav = BootstrapNav('//div[@id="stack_prop"]//ul')

    @View.nested
    class relationships(Accordion):     # noqa
        nav = BootstrapNav('//div[@id="stack_rel"]//ul')


class StackEntities(BaseEntitiesView):
    """The entities on the main list page"""
    table = Table("//div[@id='gtl_div']//table")
    # todo: remove table and use entities instead


class StackDetailsEntities(View):
    """The entties on the detail page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    lifecycle = SummaryTable(title='Lifecycle')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    # element attributes changed from id to class in upstream-fine+, capture both with locator


class StackSecurityGroupsEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    security_groups = Table('//div[@id="list_grid"]//table')


class StackParametersEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    parameters = Table('//div[@id="list_grid"]//table')


class StackOutputsEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    outputs = Table('//div[@id="list_grid"]//table')


class StackResourcesEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    resources = Table('//div[@id="list_grid"]//table')


class StackView(BaseLoggedInPage):
    """The base view for header and nav checking"""
    @property
    def in_stacks(self):
        """Determine if the Stacks page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Stacks']
        )


class StackAllView(StackView):
    """The main list page"""
    toolbar = View.nested(StackToolbar)
    including_entities = View.include(StackEntities, use_parent=True)
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return self.in_stacks and self.entities.title.text == 'Orchestration Stacks'


class ProviderStackAllView(StackAllView):

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        msg = '{} (All Orchestration Stacks)'.format(self.context['object'].name)
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
            self.entities.title.text == msg
        )


class StackDetailsView(StackView):
    """The detail page"""
    toolbar = View.nested(StackDetailsToolbar)
    sidebar = View.nested(StackDetailsAccordion)
    entities = View.nested(StackDetailsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_stacks and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class StackSecurityGroupsView(StackView):
    """The resources page"""
    toolbar = View.nested(StackSubpageToolbar)
    sidebar = View.nested(StackDetailsAccordion)
    entities = View.nested(StackSecurityGroupsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Security Groups)'.format(self.context['object'].name)
        return (
            self.in_stacks and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class StackParametersView(StackView):
    """The resources page"""
    toolbar = View.nested(StackSubpageToolbar)
    sidebar = View.nested(StackDetailsAccordion)
    entities = View.nested(StackParametersEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Parameters)'.format(self.context['object'].name)
        return (
            self.in_stacks and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class StackOutputsView(StackView):
    """The resources page"""
    toolbar = View.nested(StackSubpageToolbar)
    sidebar = View.nested(StackDetailsAccordion)
    entities = View.nested(StackOutputsEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Outputs)'.format(self.context['object'].name)
        return (
            self.in_stacks and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class StackResourcesView(StackView):
    """The resources page"""
    toolbar = View.nested(StackSubpageToolbar)
    sidebar = View.nested(StackDetailsAccordion)
    entities = View.nested(StackResourcesEntities)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Resources)'.format(self.context['object'].name)
        return (
            self.in_stacks and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


@attr.s
class Stack(Pretty, BaseEntity, WidgetasticTaggable):
    _param_name = "Stack"
    pretty_attrs = ['name']

    name = attr.ib()
    provider = attr.ib()
    quad_name = attr.ib(default='stack')

    @property
    def exists(self):
        view = navigate_to(self.parent, 'All')
        view.toolbar.view_selector.select('List View')
        try:
            view.paginator.find_row_on_pages(view.table, name=self.name)
            return True
        except NoSuchElementException:
            return False

    def delete(self):
        """Delete the stack from detail view"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Orchestration Stack', handle_alert=True)
        view.flash.assert_success_message('The selected Orchestration Stacks was deleted')

        def refresh():
            """Refresh the view"""
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.selenium.refresh()
            view.flush_widget_cache()

        wait_for(lambda: not self.exists, fail_condition=False, fail_func=refresh, num_sec=15 * 60,
                 delay=30, message='Wait for stack to be deleted')

    def wait_for_exists(self):
        """Wait for the row to show up"""
        view = navigate_to(self.parent, 'All')

        def refresh():
            """Refresh the view"""
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.refresh()
            view.flush_widget_cache()

        wait_for(lambda: self.exists, fail_condition=False, fail_func=refresh, num_sec=15 * 60,
                 delay=30, message='Wait for stack to exist')

    def retire_stack(self, wait=True):
        view = navigate_to(self.parent, 'All')
        view.toolbar.view_selector.select('List View')
        row = view.paginator.find_row_on_pages(view.table, name=self.name)
        row[0].check()
        view.toolbar.lifecycle.item_select('Retire selected Orchestration Stacks',
                                           handle_alert=True)
        view.flash.assert_success_message('Retirement initiated for 1 Orchestration'
                                                   ' Stack from the CFME Database')
        if wait:
            def refresh():
                """Refresh the view"""
                if self.provider:
                    self.provider.refresh_provider_relationships()
                view.browser.refresh()
                view.flush_widget_cache()

            wait_for(lambda: not self.exists, fail_condition=False, fail_func=refresh, delay=30,
                     num_sec=15 * 60, message='Wait for stack to be deleted')


@attr.s
class StackCollection(BaseCollection):
    """Collection class for cfme.cloud.stack.Stack"""

    ENTITY = Stack

    def delete(self, *stacks):
        stacks = list(stacks)
        stack_names = {stack.name for stack in stacks}
        checked_stack_names = set()

        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')

        for stack in stacks:
            try:
                row = view.paginator.find_row_on_pages(view.table, name=stack.name)
                row[0].check()
                checked_stack_names.add(stack.name)
            except NoSuchElementException:
                break

        if stack_names == checked_stack_names:
            if self.appliance.version < '5.9':
                view.toolbar.configuration.item_select(
                    'Remove Orchestration Stacks', handle_alert=True)
            else:
                view.toolbar.configuration.item_select(
                    'Remove Orchestration Stacks from Inventory', handle_alert=True)
            view.flash.assert_no_error()
            flash_msg = \
                'Delete initiated for {} Orchestration Stacks from the CFME Database'.format(
                    len(stacks))
            view.flash.assert_success_message(flash_msg)

            for stack in stacks:
                wait_for(lambda: not stack.exists, num_sec=15 * 60,
                     delay=30, message='Wait for stack to be deleted')
        else:
            raise ValueError(
                'Some Stacks ({!r}) not found in the UI'.format(stack_names - checked_stack_names))


@navigator.register(StackCollection, 'All')
class All(CFMENavigateStep):
    VIEW = StackAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Go to the all page"""
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Stacks')

    def resetter(self):
        """Reset the view"""
        self.view.toolbar.view_selector.select('Grid View')
        self.view.paginator.reset_selection()


@navigator.register(Stack, 'Details')
class Details(CFMENavigateStep):
    VIEW = StackDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        """Go to the details page"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.paginator.find_row_on_pages(
            self.prerequisite_view.table, name=self.obj.name)
        row.click()


@navigator.register(Stack, 'RelationshipSecurityGroups')
class RelationshipsSecurityGroups(CFMENavigateStep):
    VIEW = StackSecurityGroupsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.sidebar.relationships.open()
        try:
            self.prerequisite_view.sidebar.relationships.nav.select(
                title='Show all Security Groups')
        except NoSuchElementException:
            raise CandidateNotFound('No security groups for stack, cannot navigate')


@navigator.register(Stack, 'RelationshipParameters')
class RelationshipParameters(CFMENavigateStep):
    VIEW = StackParametersView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.sidebar.relationships.open()
        try:
            self.prerequisite_view.sidebar.relationships.nav.select(title='Show all Parameters')
        except NoSuchElementException:
            raise CandidateNotFound('No parameters for stack, cannot navigate')


@navigator.register(Stack, 'RelationshipOutputs')
class RelationshipOutputs(CFMENavigateStep):
    VIEW = StackOutputsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.sidebar.relationships.open()
        try:
            self.prerequisite_view.sidebar.relationships.nav.select(title='Show all Outputs')
        except NoSuchElementException:
            raise CandidateNotFound('No outputs for stack, cannot navigate')


@navigator.register(Stack, 'RelationshipResources')
class RelationshipResources(CFMENavigateStep):
    VIEW = StackResourcesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.sidebar.relationships.open()
        try:
            self.prerequisite_view.sidebar.relationships.nav.select(title='Show all Resources')
        except NoSuchElementException:
            raise CandidateNotFound('No resources for stack, cannot navigate')
