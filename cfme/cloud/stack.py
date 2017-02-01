from functools import partial
from xml.sax.saxutils import quoteattr

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

import cfme.fixtures.pytest_selenium as sel
from cfme import web_ui as ui
from cfme.exceptions import DestinationNotFound, StackNotFound, CandidateNotFound
from cfme.web_ui import Quadicon, flash, Form, fill, form_buttons, paginator, toolbar as tb, \
    match_location, accordion
from cfme.exceptions import CFMEException, FlashMessageException
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.pretty import Pretty
from utils.wait import wait_for


cfg_btn = partial(tb.select, "Configuration")
pol_btn = partial(tb.select, 'Policy')
lifecycle_btn = partial(tb.select, 'Lifecycle')

edit_tags_form = Form(
    fields=[
        ("select_tag", ui.Select("select#tag_cat")),
        ("select_value", ui.Select("select#tag_add"))
    ])

match_page = partial(match_location, controller='orchestration_stack',
                     title='Stacks')


class Stack(Pretty, Navigatable):
    pretty_attrs = ['name']

    def __init__(self, name, provider, quad_name=None, appliance=None):
        self.name = name
        self.quad_name = quad_name or 'stack'
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    def find_quadicon(self):
        """Find and return the quadicon belonging to this stack

    Args:
    Returns: :py:class:`cfme.web_ui.Quadicon` instance
    """
        paginator.results_per_page(100)
        for page in paginator.pages():
            quadicon = Quadicon(self.name, self.quad_name)
            if sel.is_displayed(quadicon):
                return quadicon
        else:
            raise StackNotFound("Stack '{}' not found in UI!".format(self.name))

    def delete(self, from_dest='All'):
        """
        Delete the stack, starting from the destination provided by from_dest
        @param from_dest: where to delete from, a valid navigation destination for Stack
        """

        # Navigate to the starting destination
        if from_dest in navigator.list_destinations(self):
            navigate_to(self, from_dest)
        else:
            msg = 'cfme.cloud.stack does not have destination {}'.format(from_dest)
            raise DestinationNotFound(msg)

        # Delete using the method appropriate for the starting destination
        if from_dest == 'All':
            sel.check(Quadicon(self.name, self.quad_name).checkbox())
            cfg_btn("Remove Orchestration Stacks", invokes_alert=True)
        elif from_dest == 'Details':
            cfg_btn("Remove this Orchestration Stack", invokes_alert=True)

        sel.handle_alert()
        # The delete initiated message may get missed if the delete is fast
        try:
            flash.assert_message_contain("Delete initiated for 1 Orchestration Stacks")
        except FlashMessageException as ex:
            if 'No flash message contains' in ex.message:
                flash.assert_message_contain("The selected Orchestration Stacks was deleted")

        self.wait_for_delete()

    def edit_tags(self, tag, value):
        navigate_to(self, 'EditTags')
        fill(edit_tags_form, {'select_tag': tag,
                              'select_value': value},
             action=form_buttons.save)
        flash.assert_success_message('Tag edits were successfully saved')
        company_tag = self.get_tags()
        if company_tag != "{}: {}".format(tag.replace(" *", ""), value):
            raise CFMEException("{} ({}) tag is not assigned!".format(tag.replace(" *", ""), value))

    def get_tags(self):
        navigate_to(self, 'Details')
        row = sel.elements("//*[(self::th or self::td) and normalize-space(.)={}]/../.."
                     "//td[img[contains(@src, 'smarttag')]]".format(quoteattr("My Company Tags")))
        company_tag = sel.text(row).strip()
        return company_tag

    def refresh_view_and_provider(self):
        self.provider.refresh_provider_relationships()
        tb.refresh()

    def wait_for_delete(self):
        def _wait_to_disappear():
            try:
                self.find_quadicon()
            except StackNotFound:
                return True
            else:
                return False

        navigate_to(self, 'All')
        wait_for(_wait_to_disappear, fail_condition=False, message="Wait stack to disappear",
                 num_sec=15 * 60, fail_func=self.refresh_view_and_provider, delay=30)

    def wait_for_appear(self):
        def _wait_to_appear():
            try:
                self.find_quadicon()
            except StackNotFound:
                return False
            else:
                return True

        navigate_to(self, 'All')
        wait_for(_wait_to_appear, fail_condition=False, message="Wait stack to appear",
                 num_sec=15 * 60, fail_func=self.refresh_view_and_provider, delay=30)

    def retire_stack(self, wait=True):
        navigate_to(self, 'All')
        sel.check(self.find_quadicon())
        lifecycle_btn("Retire this Orchestration Stack", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Retirement initiated for 1 Orchestration'
        ' Stack from the CFME Database')
        if wait:
            self.wait_for_delete()


@navigator.register(Stack, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Orchestration Stacks')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Stacks')

    def resetter(self):
        tb.select('Grid View')
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Stack, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        sel.click(self.obj.find_quadicon())


@navigator.register(Stack, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(Stack, 'RelationshipSecurityGroups')
class RelationshipsSecurityGroups(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (All Security Groups)'.format(self.obj.name))

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        try:
            sel.click('//*[@id="stack_rel"]//a[@title="Show all Security Groups"]')
        except NoSuchElementException:
            raise CandidateNotFound('No security groups for stack, cannot navigate')


@navigator.register(Stack, 'RelationshipParameters')
class RelationshipParameters(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (Parameters)'.format(self.obj.name))

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        sel.click('//*[@id="stack_rel"]//a[@title="Show all Parameters"]')


@navigator.register(Stack, 'RelationshipOutputs')
class RelationshipOutputs(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (Outputs)'.format(self.obj.name))

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        try:
            sel.click('//*[@id="stack_rel"]//a[@title="Show all Outputs"]')
        except NoSuchElementException:
            raise CandidateNotFound('No Outputs for stack, cannot navigate')


@navigator.register(Stack, 'RelationshipResources')
class RelationshipResources(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return match_page(summary='{} (Resources)'.format(self.obj.name))

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        sel.click('//*[@id="stack_rel"]//a[@title="Show all Resources"]')
