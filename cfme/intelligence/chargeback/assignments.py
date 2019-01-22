# -*- coding: utf-8 -*-
# Page model for Intel->Chargeback->Assignments.
import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic_patternfly import BootstrapSelect, Button

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.update import Updateable
from widgetastic_manageiq import Table
from widgetastic_manageiq.hacks import BootstrapSelectByLocator
from . import ChargebackView


class AssignmentsAllView(ChargebackView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and self.title.text == "All Assignments"
        )


class AssignmentsView(ChargebackView):
    title = Text("#explorer_title_text")
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_chargeback and
            self.title.text == '{} Rate Assignments'.format(
                self.context["object"].assign_type) and
            self.assignments.is_opened and
            self.assignments.tree.currently_selected == [
                "Assignments",
                self.context["object"].assign_type
            ]
        )

    assign_to = BootstrapSelect(id="cbshow_typ")
    tag_category = BootstrapSelect(id='cbtag_cat')
    docker_labels = BootstrapSelect(id='cblabel_key')
    _table_locator = '//h3[contains(text(),"Selections")]/following-sibling::table'
    _table_widget_locator = './/div[contains(@class, "bootstrap-select")]'

    selections = Table(
        locator=_table_locator,
        column_widgets={'Rate': BootstrapSelectByLocator(locator=_table_widget_locator)},
        assoc_column=0,
    )


@attr.s
class Assign(Updateable, BaseEntity):
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
        enterprise = appliance.collections.assignments.instantiate(
            assign_to =  "The Enterprise",
            assign_type = "Compute", # or "Storage"
            selections={
            'Enterprise': {'Rate': 'Default'}
        })
        enterprise.assign()
    """
    assign_to = attr.ib()
    assign_type = attr.ib()
    tag_category = attr.ib(default=None)
    docker_labels = attr.ib(default=None)
    selections = attr.ib(default=None)

    def assign(self):
        view = navigate_to(self, 'Details')
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


@attr.s
class AssignsCollection(BaseCollection):
    """Collection object for the
    :py:class:'cfme.intelligence.chargeback.assignments.Assign'."""

    ENTITY = Assign


@navigator.register(AssignsCollection, "All")
class AssignAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'IntelChargeback')
    VIEW = AssignmentsAllView

    def step(self):
        self.view.assignments.tree.click_path("Assignments")


@navigator.register(Assign, 'Details')
class AssignDetails(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = AssignmentsView

    def step(self):

        self.view.assignments.tree.click_path("Assignments", self.obj.assign_type)
