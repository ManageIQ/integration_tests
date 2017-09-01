# -*- coding: utf-8 -*-
# Page model for Intel->Chargeback->Assignments.

from . import ChargebackView
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import Text
from widgetastic_manageiq import Table
from widgetastic_manageiq.hacks import BootstrapSelectByLocator
from widgetastic_patternfly import BootstrapSelect, Button, FlashMessages
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


class AssignmentsAllView(ChargebackView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == "All Assignments"
        )


class AssignmentsView(ChargebackView):
    title = Text("#explorer_title_text")
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == '"{}" Rate Assignments'.format(
                self.context["object"].description) and
            self.assignments.is_opened and
            self.rates.tree.currently_selected == [
                "{} Rate Assignments",
                self.context["object"].description
            ]
        )

    assign_to = BootstrapSelect(id="cbshow_typ")
    tag_category = BootstrapSelect(id='cbtag_cat')
    docker_labels = BootstrapSelect(id='cblabel_key')
    _table_locator = '//h3[contains(text(),"Selections")]/following-sibling::table'
    _table_widget_locator = './/div[contains(@class, "bootstrap-select")]'

    selections = Table(locator=_table_locator,
            column_widgets={'Rate': BootstrapSelectByLocator(locator=_table_widget_locator)},
            assoc_column=0)


class Assign(Updateable, Pretty, Navigatable):
    """
    Model of Chargeback Assignment page in cfme.

    Args:
        assign_to: Assign the chargeback rate to entities such as VM,Provider,datastore or the
            Enterprise itself.
        tag_category: Tag category of the entity
        selections: Selection of a particular entity to which the rate is to be assigned.
            Eg:If the chargeback rate is to be assigned to providers,select which of the managed
            providers the rate is to be assigned.

    Usage:
        enterprise = Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': 'Default'}
        })
    enterprise.computeassign()

    """
    def __init__(self, assign_to=None,
                 tag_category=None,
                 docker_labels=None,
                 selections=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.assign_to = assign_to
        self.tag_category = tag_category
        self.docker_labels = docker_labels
        self.selections = selections

    def storageassign(self):
        view = navigate_to(self, 'Storage')
        was_change = self._fill(view)
        if was_change:
            view.save_button.click()
        view.flash.assert_no_error()
        view.flash.assert_message('Rate Assignments saved')

    def computeassign(self):
        view = navigate_to(self, 'Compute')
        was_change = self._fill(view)
        if was_change:
            view.save_button.click()
        view.flash.assert_no_error()
        view.flash.assert_message('Rate Assignments saved')

    def _fill(self, view):
        """This function prepares the values and fills the form."""
        fill_details = dict(
            assign_to=self.assign_to,
            tag_category=self.tag_category,
            docker_labels=self.docker_labels,
            selections=self.selections,
        )
        return view.fill(fill_details)


@navigator.register(Assign, 'All')
class AssignAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')
    VIEW = AssignmentsAllView

    def step(self):
        self.view.assignments.tree.click_path(
            "Assignments"
        )


@navigator.register(Assign, 'Storage')
class AssignStorage(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = AssignmentsView

    def step(self):
        self.view.assignments.tree.click_path(
            "Assignments", "Storage")


@navigator.register(Assign, 'Compute')
class AssignCompute(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = AssignmentsView

    def step(self):
        self.view.assignments.tree.click_path(
            "Assignments", "Compute")
