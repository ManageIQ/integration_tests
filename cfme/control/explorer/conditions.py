# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import Widget
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.control.explorer import ControlExplorerView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from widgetastic_manageiq.expression_editor import ExpressionEditor


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
            # there is a BZ 1683697 that some Condition view is shown for All Conditions
            self.title.text == "All Conditions" if not False else True and
            self.conditions.is_opened and
            self.conditions.tree.currently_selected == ["All Conditions"]
        )


class ConditionFormCommon(ControlExplorerView):

    title = Text("#explorer_title_text")
    description = Input(name="description")
    scope = ExpressionEditor("//button[normalize-space(.)='Define Scope']")
    expression = ExpressionEditor("//button[normalize-space(.)='Define Expression']")
    notes = TextInput(name="notes")

    cancel_button = Button("Cancel")


class NewConditionView(ConditionFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        expected_tree = [
            "All Conditions",
            "{} Conditions".format(self.context["object"].TREE_NODE)
        ]
        return (
            self.in_control_explorer and
            self.title.text == "Adding a new Condition" and
            self.conditions.is_opened and
            self.conditions.tree.currently_selected == expected_tree
        )


class ConditionClassAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All {} Conditions".format(self.context["object"].FIELD_VALUE) and
            self.conditions.is_opened and
            self.conditions.tree.currently_selected ==
            ["All Conditions", "{} Conditions".format(self.context["object"].TREE_NODE)]
        )


class EditConditionView(ConditionFormCommon):
    fill_strategy = WaitFillViewStrategy()
    title = Text("#explorer_title_text")

    save_button = Button("Save")
    cancel_button = Button("Cancel")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Editing {} Condition "{}"'.format(
                self.context["object"].FIELD_VALUE,
                self.context["object"].description
            ) and
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
            # TODO add in a check against the tree once BZ 1683697 is fixed
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
        """
        view = navigate_to(self, "Edit")
        view.fill(updates)
        view.save_button.click()
        view = self.create_view(ConditionDetailsView, override=updates, wait="10s")
        view.flash.assert_success_message(
            'Condition "{}" was saved'.format(updates.get("description", self.description))
        )

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
            view = self.create_view(ConditionClassAllView, wait="20s")
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
        try:
            self.appliance.rest_api.collections.conditions.get(description=self.description)
            return True
        except ValueError:
            return False


@attr.s
class ConditionCollection(BaseCollection):

    ENTITY = BaseCondition

    def create(self, condition_class, description, expression=None, scope=None, notes=None):
        condition = condition_class(self, description, expression=expression, scope=scope,
            notes=notes)
        view = navigate_to(condition, "Add")
        # first fill description, expression, and notes
        view.fill({
            "description": condition.description,
            "expression": condition.expression,
            "scope": condition.scope,
            "notes": condition.notes
        })
        view.wait_displayed()
        view.add_button.click()
        view = condition.create_view(ConditionDetailsView, wait="10s")
        view.flash.assert_success_message('Condition "{}" was added'.format(condition.description))
        return condition

    def all(self):
        raise NotImplementedError


@navigator.register(ConditionCollection, "All")
class AllConditions(CFMENavigateStep):
    VIEW = ConditionsAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self, *args, **kwargs):
        self.prerequisite_view.conditions.tree.click_path("All Conditions")


@navigator.register(BaseCondition, "Add")
class ConditionNew(CFMENavigateStep):
    VIEW = NewConditionView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
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

    def step(self, *args, **kwargs):
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

    def step(self, *args, **kwargs):
        self.prerequisite_view.conditions.tree.click_path(
            "All Conditions",
            "{} Conditions".format(self.obj.TREE_NODE),
            self.obj.description
        )


@navigator.register(BaseCondition, "Details in policy")
class PolicyConditionDetails(CFMENavigateStep):
    VIEW = ConditionPolicyDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self, *args, **kwargs):
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

    TREE_NODE = "Replicator"
    PRETTY = FIELD_VALUE = "Container Replicator"


class PodCondition(BaseCondition):

    TREE_NODE = "Pod"
    PRETTY = FIELD_VALUE = "Container Pod"


class ContainerNodeCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Container Node"


class ContainerImageCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Container Image"


class ProviderCondition(BaseCondition):

    TREE_NODE = PRETTY = FIELD_VALUE = "Provider"
