from functools import partial
from xml.sax.saxutils import quoteattr

from navmazing import NavigateToSibling, NavigateToAttribute

import cfme.fixtures.pytest_selenium as sel
from cfme import web_ui as ui
from cfme.exceptions import DestinationNotFound
from cfme.web_ui import Quadicon, flash, Form, fill, form_buttons, paginator, toolbar as tb, \
    summary_title, accordion
from cfme.exceptions import CFMEException, FlashMessageException
from utils.appliance import Navigatable
from utils.appliance.endpoints.ui import navigator, navigate_to, CFMENavigateStep
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


def match_title_and_controller():
    title_match = sel.execute_script('return document.title;') == 'CFME: Stacks'
    controller_match = sel.execute_script('return ManageIQ.controller;') == 'orchestration_stack'
    return title_match and controller_match


class Stack(Pretty, Navigatable):
    pretty_attrs = ['name']

    def __init__(self, name=None, quad_name=None, appliance=None):
        self.name = name
        self.quad_name = quad_name or 'stack'
        Navigatable.__init__(self, appliance=appliance)

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
        pol_btn('Edit Tags', invokes_alert=True)
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

    def wait_for_delete(self):
        navigate_to(self, 'All')
        wait_for(lambda: not sel.is_displayed(Quadicon(self.name, self.quad_name)),
            fail_condition=False, message="Wait stack to disappear", num_sec=500,
            fail_func=sel.refresh)

    def wait_for_appear(self):
        navigate_to(self, 'All')
        wait_for(lambda: sel.is_displayed(Quadicon(self.name, self.quad_name)),
            fail_condition=False, message="Wait stack to appear", num_sec=1000,
            fail_func=sel.refresh)

    def retire_stack(self, wait=True):
        navigate_to(self, 'All')
        sel.check(Quadicon(self.name, self.quad_name).checkbox())
        lifecycle_btn("Retire this Orchestration Stack", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Retirement initiated for 1 Orchestration'
        ' Stack from the CFME Database')
        if wait:
            self.wait_for_delete()


@navigator.register(Stack, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance', 'LoggedIn')

    def am_i_here(self):
        summary_match = summary_title() == 'Orchestration Stacks'
        return match_title_and_controller() and summary_match

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Clouds', 'Stacks')(None)

    def resetter(self):
        tb.select('Grid View')
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Stack, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        summary_match = summary_title() == '{} (Summary)'.format(self.obj.name)
        return match_title_and_controller() and summary_match

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(Stack, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(Stack, 'RelationshipSecurityGroups')
class RelationshipsSecurityGroups(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        summary_match = summary_title() == '{} (All Security Groups)'.format(self.obj.name)
        return match_title_and_controller() and summary_match

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        sel.click('//*[@id="stack_rel"]//a[@title="Show all Security Groups"]')


@navigator.register(Stack, 'RelationshipParameters')
class RelationshipParameters(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        summary_match = summary_title() == '{} (Parameters)'.format(self.obj.name)
        return match_title_and_controller() and summary_match

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        sel.click('//*[@id="stack_rel"]//a[@title="Show all Parameters"]')


@navigator.register(Stack, 'RelationshipOutputs')
class RelationshipOutputs(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        summary_match = summary_title() == '{} (Outputs)'.format(self.obj.name)
        return match_title_and_controller() and summary_match

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        sel.click('//*[@id="stack_rel"]//a[@title="Show all Outputs"]')


@navigator.register(Stack, 'RelationshipResources')
class RelationshipResources(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        summary_match = summary_title() == '{} (Resources)'.format(self.obj.name)
        return match_title_and_controller() and summary_match

    def step(self):
        accordion.click('Relationships')
        # Click by anchor title since text contains a dynamic component
        sel.click('//*[@id="stack_rel"]//a[@title="Show all Resources"]')
