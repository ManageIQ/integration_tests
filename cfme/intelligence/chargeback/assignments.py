# -*- coding: utf-8 -*-
# Page model for Intel->Chargeback->Assignments.

import cfme.fixtures.pytest_selenium as sel
from . import ChargebackView
from collections import Mapping
from copy import copy
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import Text
from cfme.web_ui import Form, fill, flash, form_buttons, Select as Select_old
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from utils.pretty import Pretty
from utils.update import Updateable
from utils.version import LOWEST, pick


class AssignmentsAllView(ChargebackView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_chargeback and
            self.title.text == "All Assignments"
        )


class AssignmentsView(ChargebackView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_chargeback and
            self.title.text == '"{}" Rate Assignments'.format(
                self.context["object"].description) and
            self.assignments.is_opened and
            self.rates.tree.currently_selected == [
                "{} Rate Assignments",
                self.context["object"].description
            ]
        )


class AssignFormTable(Pretty):
    pretty_attrs = ["entry_loc"]

    def __init__(self, entry_loc):
        self.entry_loc = entry_loc

    def locate(self):
        return self.entry_loc

    @property
    def rows(self):
        return sel.elements("./tbody/tr", root=self)

    def row_by_name(self, name):
        for row in self.rows:
            row_name = sel.text_sane(sel.element("./td[1]", root=row))
            if row_name == name:
                return row
        else:
            raise NameError("Did not find row named {}!".format(name))

    def select_from_row(self, row):
        el = pick({"5.6": "./td/select",
                   "5.7": "./td/div/select"})
        return Select_old(sel.element(el, root=row))

    def select_by_name(self, name):
        return self.select_from_row(self.row_by_name(name))


@fill.method((AssignFormTable, Mapping))
def _fill_assignform_dict(form, d):
    d = copy(d)  # Mutable
    for name, value in d.iteritems():
        if value is None:
            value = "<Nothing>"
        select = form.select_by_name(name)
        sel.select(select, value)


assign_form = Form(
    fields=[
        ("assign_to", Select_old("select#cbshow_typ")),
        # Enterprise
        ("enterprise", Select_old("select#enterprise__1")),  # Simple shotcut, might explode once
        # Tagged DS
        ("tag_category", Select_old("select#cbtag_cat")),
        # Docker Labels
        ("docker_labels", Select_old('select#cblabel_key')),
        # Common - selection table
        ("selections", AssignFormTable({
            LOWEST: (
                "//div[@id='cb_assignment_div']/fieldset/table[contains(@class, 'style1')]"
                "/tbody/tr/td/table"),
            "5.4": "//div[@id='cb_assignment_div']/table[contains(@class, 'table')]",
        })),
        ('save_button', form_buttons.save)])


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
        tagged_datastore = Assign(
            assign_to="Tagged Datastores",
            tag_category="Location",
            selections={
                "Chicago": "Default"
        })
    tagged_datastore.storageassign()

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
        navigate_to(self, 'Storage')
        fill(assign_form,
            {'assign_to': self.assign_to,
             'tag_category': self.tag_category,
             'selections': self.selections},
            action=assign_form.save_button)
        flash.assert_no_errors()

    def computeassign(self):
        navigate_to(self, 'Compute')
        fill(assign_form,
            {'assign_to': self.assign_to,
             'tag_category': self.tag_category,
             'docker_labels': self.docker_labels,
             'selections': self.selections},
            action=assign_form.save_button)
        flash.assert_no_errors()


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
