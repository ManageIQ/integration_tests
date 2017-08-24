from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Button, Dropdown, FlashMessages, BootstrapNav
from widgetastic_manageiq import (
    Accordion, BootstrapSelect, BreadCrumb, ItemsToolBarViewSelector, PaginationPane, Search,
    SummaryTable, Table, Text)

from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import DestinationNotFound, StackNotFound, CandidateNotFound
from cfme.web_ui import match_location
from cfme.exceptions import CFMEException
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.pretty import Pretty
from utils.wait import wait_for


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


class StackEntities(View):
    """The entties on the main list page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class StackDetailsEntities(View):
    """The entties on the detail page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    lifecycle = SummaryTable(title='Lifecycle')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class StackEditTagEntities(View):
    """The entities on the edit tags page"""
    breadcrumb = BreadCrumb()
    title = Text('#explorer_title_text')


class StackSecurityGroupsEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    security_groups = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class StackParametersEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    parameters = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class StackOutputsEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    outputs = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class StackResourcesEntities(View):
    """The entities of the resources page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    resources = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class StackView(BaseLoggedInPage):
    """The base view for header and nav checking"""
    @property
    def in_stacks(self):
        """Determine if the Stacks page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Stacks'] and
            # TODO: Needs to be converted once there's a Widgetastic alternative
            match_location(controller='orchestration_stack', title='Stacks'))


class StackAllView(StackView):
    """The main list page"""
    toolbar = View.nested(StackToolbar)
    entities = View.nested(StackEntities)
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return self.in_stacks and self.entities.title.text == 'Orchestration Stacks'


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


class StackEditTagsForm(View):
    """The form on the edit tags page"""
    select_tag = BootstrapSelect('tag_cat')
    select_value = BootstrapSelect('tag_add')
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel = Button('Cancel')


class StackEditTagsView(StackView):
    """The edit tags page"""
    entities = View.nested(StackEditTagEntities)
    form = View.nested(StackEditTagsForm)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_stacks and
            self.entities.breadcrumb.locations == [
                'Orchestration Stacks', '{} (Summary)'.format(self.context['object'].name),
                'Tag Assignment'] and
            self.entities.breadcrumb.active_location == 'Tag Assignment')


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


class StackCollection(Navigatable):
    """Collection class for cfme.cloud.stack.Stack"""

    def instantiate(self, name, provider, quad_name=None):
        return Stack(name, provider, quad_name=quad_name, collection=self)

    def delete(self, *stacks):
        stacks = list(stacks)
        checked_stacks = list()

        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')

        for stack in stacks:
            try:
                row = view.paginator.find_row_on_pages(view.entities.table, name=stack.name)
                row[0].check()
                checked_stacks.append(stack)
            except NoSuchElementException:
                break

        if set(stacks) == set(checked_stacks):
            view.toolbar.configuration.item_select('Remove Orchestration Stacks', handle_alert=True)
            view.entities.flash.assert_no_error()
            flash_msg = \
                'Delete initiated for {} Orchestration Stacks from the CFME Database'.format(
                    len(stacks))
            view.entities.flash.assert_success_message(flash_msg)

            for stack in stacks:
                wait_for(lambda: not stack.exists, num_sec=15 * 60,
                     delay=30, message='Wait for stack to be deleted')
        else:
            raise ValueError('Some Stacks not found in the UI')


class Stack(Pretty, Navigatable):
    _param_name = "Stack"
    pretty_attrs = ['name']

    def __init__(self, name, provider, quad_name=None, collection=None):
        self.name = name
        self.quad_name = quad_name or 'stack'
        self.provider = provider
        self.collection = collection or StackCollection()
        Navigatable.__init__(self, appliance=self.collection.appliance)

    @property
    def exists(self):
        view = navigate_to(self.collection, 'All')
        view.toolbar.view_selector.select('List View')
        try:
            view.paginator.find_row_on_pages(view.entities.table, name=self.name)
            return True
        except NoSuchElementException:
            return False

    def delete(self):
        """Delete the stack from detail view"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Orchestration Stack', handle_alert=True)
        view.entities.flash.assert_success_message('The selected Orchestration Stacks was deleted')

        def refresh():
            """Refresh the view"""
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.selenium.refresh()
            view.flush_widget_cache()

        wait_for(lambda: not self.exists, fail_condition=False, fail_func=refresh, num_sec=15 * 60,
                 delay=30, message='Wait for stack to be deleted')

    def edit_tags(self, tag, value):
        """Edit the tags of a particular stack"""
        view = navigate_to(self, 'EditTags')
        view.form.fill({'select_tag': tag, 'select_value': value})
        view.form.save_button.click()
        detail_view = self.create_view(StackDetailsView)
        detail_view.entities.flash.assert_success_message('Tag edits were successfully saved')
        company_tag = self.get_tags()
        if company_tag != "{}: {}".format(tag.replace(" *", ""), value):
            raise CFMEException("{} ({}) tag is not assigned!".format(tag.replace(" *", ""), value))

    def get_tags(self):
        view = navigate_to(self, 'Details')
        company_tag = view.entities.smart_management.get_text_of('My Company Tags')
        return company_tag

    def wait_for_exists(self):
        """Wait for the row to show up"""
        view = navigate_to(self.collection, 'All')

        def refresh():
            """Refresh the view"""
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.refresh()
            view.flush_widget_cache()

        wait_for(lambda: self.exists, fail_condition=False, fail_func=refresh, num_sec=15 * 60,
                 delay=30, message='Wait for stack to exist')

    def retire_stack(self, wait=True):
        view = navigate_to(self.collection, 'All')
        view.toolbar.view_selector.select('List View')
        row = view.paginator.find_row_on_pages(view.entities.table, name=self.name)
        row[0].check()
        view.toolbar.lifecycle.item_select('Retire selected Orchestration Stacks',
                                           handle_alert=True)
        view.entities.flash.assert_success_message('Retirement initiated for 1 Orchestration'
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
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(Stack, 'Details')
class Details(CFMENavigateStep):
    VIEW = StackDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        """Go to the details page"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        row = self.prerequisite_view.paginator.find_row_on_pages(
            self.prerequisite_view.entities.table, name=self.obj.name)
        row.click()


@navigator.register(Stack, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = StackEditTagsView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Go to the edit tags screen"""
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


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
