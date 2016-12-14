# -*- coding: utf-8 -*-
from utils.pretty import Pretty
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from navmazing import NavigateToAttribute

from widgetastic.widget import Text, TextInput, Widget
from widgetastic_patternfly import Button, Input

from . import ControlExplorerView
from utils.appliance import Navigatable
from utils.update import Updateable

from cfme.web_ui.expression_editor_widgetastic import ExpressionEditor


class Expression(Widget):
    ROOT = "div#condition_info_div"

    def __init__(self, parent, type_, logger=None):
        Widget.__init__(self, parent, logger=logger)
        if type_ not in ["Scope", "Expression"]:
            raise ValueError("Type should be Scope or Expression only")
        else:
            self.type = type_

    def __locator__(self):
        return self.ROOT

    @property
    def text_list(self):
        return self.browser.element(self).text.split("\n")

    def read(self):
        """
        In Condition details view Scope and Expression don't have any locator. So we
        have to scrape whole text in the parent div and split it by "\\n". After that in text_list
        we receive something like that:

        .. code-block:: python

          [u'Scope',
           u'COUNT OF VM and Instance.Files > 150',
           u'Expression',
           u'VM and Instance : Boot Time BEFORE "03/04/2014 00:00"',
           u'Notes',
           u'No notes have been entered.',
           u'Assigned to Policies',
           u'This Condition is not assigned to any Policies.']

        To get value of Scope or Expression firstly we find its index in the list and then just
        seek next member.
        """
        index = self.text_list.index(self.type)
        return self.text_list[index + 1]


class ConditionsAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All {} Conditions".format(self.context["object"].FIELD_VALUE) and
            self.conditions.is_opened and
            self.conditions.tree.currently_selected == ["All Conditions",
                "{} Conditions".format(self.context["object"].TREE_NODE)]
        )


class ConditionFormCommon(ControlExplorerView):

    title = Text("#explorer_title_text")
    description = Input(name="description")
    scope = ExpressionEditor("//img[@alt='Edit this Scope']")
    expression = ExpressionEditor("//img[@alt='Edit this Expression']")
    notes = TextInput(name="notes")

    cancel_button = Button("Cancel")


class NewConditionView(ConditionFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "Adding a new Condition" and
            self.conditions.is_opened and
            self.conditions.tree.currently_selected == ["All Conditions",
                "{} Condition".format(self.context["object"].TREE_NODE)]
        )


class EditConditionView(ConditionFormCommon):
    title = Text("#explorer_title_text")

    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == '{} "{}"'.format(self.context["object"].FIELD_VALUE,
                self.context["object"].description) and
            self.conditions.is_opened and
            self.conditions.tree.currently_selected == [
                "All Conditions",
                "{} Conditions".format(self.context["object"].TREE_NODE),
                self.context["object"].description
            ]
        )


class ConditionDetailsView(ControlExplorerView):
    title = Text("#explorer_title_text")
    scope = Expression("Scope")
    expression = Expression("Expression")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == '{} Condition "{}"'.format(self.context["object"].FIELD_VALUE,
                self.context["object"].description) and
            self.conditions.is_opened
        )


class BaseCondition(Updateable, Navigatable, Pretty):

    TREE_NODE = None
    PRETTY = None
    FIELD_VALUE = None

    def __init__(self, description, expression=None, scope=None, notes=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.expression = expression
        self.scope = scope
        self.notes = notes

    def create(self):
        view = navigate_to(self, "Add")
        view.fill({
            "description": self.description,
            "expression": self.expression,
            "scope": self.scope,
            "notes": self.notes
        })
        view.add_button.click()
        view = self.create_view(ConditionDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Condition "{}" was added'.format(self.description))

    def update(self, updates):
        """Update this Condition in UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        view = navigate_to(self, "Edit")
        view.fill(updates)
        view.save_button.click()
        view = self.create_view(ConditionDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message(
            'Condition "{}" was saved'.format(updates.get("description", self.description)))

    def delete(self, cancel=False):
        """Delete this Condition in UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this {} Condition".format(self.FIELD_VALUE),
            handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(ConditionsAllView)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message('Condition "{}": Delete successful'.format(self.description))

    def read_expression(self):
        view = navigate_to(self, "Details")
        assert view.is_displayed
        return view.expression.read()

    def read_scope(self):
        view = navigate_to(self, "Details")
        assert view.is_displayed
        return view.scope.read()

    @property
    def exists(self):
        """Check existence of this Condition.

        Returns: :py:class:`bool` signalizing the presence of the Condition in the database.
        """
        conditions = self.appliance.db["conditions"]
        return self.appliance.db.session\
            .query(conditions.description)\
            .filter(conditions.description == self.description)\
            .count() > 0


@navigator.register(BaseCondition, "Add")
class ConditionNew(CFMENavigateStep):
    VIEW = NewConditionView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE)
        )
        self.view.configuration.item_select("Add a New {} Condition".format(self.obj.PRETTY))


@navigator.register(BaseCondition, "Edit")
class ConditionEdit(CFMENavigateStep):
    VIEW = EditConditionView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE),
            self.obj.description
        )
        self.view.configuration.item_select("Edit this Condition")


@navigator.register(BaseCondition, "Details")
class ConditionDetails(CFMENavigateStep):
    VIEW = ConditionDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE),
            self.obj.description
        )


class HostCondition(BaseCondition):

    TREE_NODE = "Host"
    PRETTY = "Host / Node"
    FIELD_VALUE = "Host / Node"


class VMCondition(BaseCondition):

    TREE_NODE = "VM and Instance"
    PRETTY = "VM"
    FIELD_VALUE = "VM and Instance"


class ReplicatorCondition(BaseCondition):

    TREE_NODE = "Replicator"
    PRETTY = "Replicator"
    FIELD_VALUE = "Replicator"


class PodCondition(BaseCondition):

    TREE_NODE = "Pod"
    PRETTY = "Pod"
    FIELD_VALUE = "Pod"


class ContainerNodeCondition(BaseCondition):

    TREE_NODE = "Container Node"
    PRETTY = "Node"
    FIELD_VALUE = "Node"


class ContainerImageCondition(BaseCondition):

    TREE_NODE = "Container Image"
    PRETTY = "Container Image"
    FIELD_VALUE = "Container Image"
