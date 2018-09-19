# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, TextInput, Widget
from widgetastic_patternfly import Button, Input

from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq.expression_editor import ExpressionEditor
from . import ControlExplorerView


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

    @property
    def text(self):
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

    def read(self):
        return self.text


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


class ConditionPolicyDetailsView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == '{} Condition "{}"'.format(
                self.context["object"].context_policy.PRETTY,
                self.context["object"].description) and
            self.policies.is_opened and
            self.policies.tree.currently_selected == [
                "All Policies",
                "{} Policies".format(self.context["object"].context_policy.TYPE),
                "{} {} Policies".format(self.context["object"].context_policy.TREE_NODE,
                    self.context["object"].context_policy.TYPE),
                self.context["object"].context_policy.description,
                self.context["object"].description
            ]
        )


@attr.s
class BaseCondition(BaseEntity, Updateable, Pretty):

    TREE_NODE = None
    PRETTY = None
    FIELD_VALUE = None
    _param_name = ParamClassName('description')

    description = attr.ib()
    expression = attr.ib(default=None)
    scope = attr.ib(default=None)
    notes = attr.ib(default=None)

    def update(self, updates):
        """Update this Condition in UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        view = navigate_to(self, "Edit")
        view.fill(updates)
        view.save_button.click()
        view = self.create_view(ConditionDetailsView, override=updates)
        wait_for(lambda: view.is_displayed, timeout=10,
            message="wait until ConditionDetailsView will be displayed")
        view.flash.assert_success_message(
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
            view.flash.assert_success_message('Condition "{}": Delete successful'.format(
                self.description))

    def read_expression(self):
        view = navigate_to(self, "Details")
        assert view.is_displayed
        return view.expression.text

    def read_scope(self):
        view = navigate_to(self, "Details")
        assert view.is_displayed
        return view.scope.text

    @property
    def exists(self):
        """Check existence of this Condition.

        Returns: :py:class:`bool` signalizing the presence of the Condition in the database.
        """
        conditions = self.appliance.db.client["conditions"]
        return self.appliance.db.client.session\
            .query(conditions.description)\
            .filter(conditions.description == self.description)\
            .count() > 0


@attr.s
class ConditionCollection(BaseCollection):

    ENTITY = BaseCondition

    def create(self, condition_class, description, expression=None, scope=None, notes=None):
        condition = condition_class(self, description, expression=expression, scope=scope,
            notes=notes)
        view = navigate_to(condition, "Add")
        view.fill({
            "description": condition.description,
            "expression": condition.expression,
            "scope": condition.scope,
            "notes": condition.notes
        })
        view.add_button.click()
        view = condition.create_view(ConditionDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message('Condition "{}" was added'.format(condition.description))
        return condition

    def all(self):
        raise NotImplementedError


@navigator.register(ConditionCollection, "All")
class AllConditions(CFMENavigateStep):
    VIEW = ConditionsAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.prerequisite_view.conditions.tree.click_path("All Conditions")


@navigator.register(BaseCondition, "Add")
class ConditionNew(CFMENavigateStep):
    VIEW = NewConditionView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE)
        )
        self.prerequisite_view.configuration.item_select(
            "Add a New {} Condition".format(self.obj.PRETTY))


@navigator.register(BaseCondition, "Edit")
class ConditionEdit(CFMENavigateStep):
    VIEW = EditConditionView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE),
            self.obj.description
        )
        self.prerequisite_view.configuration.item_select("Edit this Condition")


@navigator.register(BaseCondition, "Details")
class ConditionDetails(CFMENavigateStep):
    VIEW = ConditionDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE),
            self.obj.description
        )


@navigator.register(BaseCondition, "Details in policy")
class PolicyConditionDetails(CFMENavigateStep):
    VIEW = ConditionPolicyDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.prerequisite_view.policies.tree.click_path(
            "All Policies",
            "{} Policies".format(self.obj.context_policy.TYPE),
            "{} {} Policies".format(
                self.obj.context_policy.TREE_NODE,
                self.obj.context_policy.TYPE
            ),
            self.obj.context_policy.description,
            self.obj.description
        )


class HostCondition(BaseCondition):

    TREE_NODE = "Host"
    PRETTY = FIELD_VALUE = "Host / Node"


class VMCondition(BaseCondition):

    FIELD_VALUE = TREE_NODE = "VM and Instance"
    PRETTY = "VM"


class ReplicatorCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Replicator"


class PodCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Pod"


class ContainerNodeCondition(BaseCondition):

    TREE_NODE = "Container Node"
    PRETTY = FIELD_VALUE = "Node"


class ContainerImageCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Container Image"


class ProviderCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Provider"
