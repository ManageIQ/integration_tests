# -*- coding: utf-8 -*-
"""Page model for Control / Explorer"""
from utils.pretty import Pretty
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from navmazing import NavigateToAttribute

from widgetastic.widget import Text
from widgetastic_manageiq import SummaryFormItem, MultiBoxSelect, ManageIQTree
from widgetastic_patternfly import BootstrapSelect, Button, Input

from . import ControlExplorerView
from utils.appliance import Navigatable
from utils.update import Updateable


class ActionsAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All Actions" and
            self.actions.tree.currently_selected == ["All Actions"]
        )


class ActionFormCommon(ControlExplorerView):

    description = Input(name="description")
    action_type = BootstrapSelect("miq_action_type")
    snapshot_name = Input(name="snapshot_name")
    analysis_profile = BootstrapSelect("analysis_profile")
    alerts_to_evaluate = MultiBoxSelect(
        "formtest",
        move_into=".//a[@data-submit='choices_chosen_div']/img",
        move_from=".//a[@data-submit='members_chosen_div']/img"
    )
    snapshot_age = BootstrapSelect("snapshot_age")
    parent_type = BootstrapSelect("parent_type")
    cpu_number = BootstrapSelect("cpu_value")
    memory_amount = Input(name="memory_value")
    email_sender = Input(name="from")
    email_recipient = Input(name="to")
    vcenter_attr_name = Input(name="attribute")
    vcenter_attr_value = Input(name="value")
    tag = ManageIQTree("action_tags_treebox")

    cancel_button = Button('Cancel')


class NewActionView(ActionFormCommon):
    title = Text("#explorer_title_text")

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "Adding a new Action" and
            self.actions.is_opened and
            self.actions.tree.currently_selected == ["All Actions"]
        )


class EditActionView(ActionFormCommon):
    title = Text("#explorer_title_text")

    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Editing Action "{}"'.format(self.context["object"].description) and
            self.actions.is_opened and
            self.actions.tree.currently_selected == [
                "All Actions",
                self.context["object"].description
            ]
        )


class ActionDetailsView(ControlExplorerView):
    title = Text("#explorer_title_text")

    type = SummaryFormItem("Basic Information", "Action Type")
    analysis_profile = SummaryFormItem("Analysis Profile", "Assigned Analysis Profile")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Action "{}"'.format(self.context["object"].description) and
            self.actions.is_opened and
            self.actions.tree.currently_selected == [
                "All Actions",
                self.context["object"].description
            ]
        )


class Action(Updateable, Navigatable, Pretty):
    """This class represents one Action.

    Example:

        >>> from cfme.control.explorer import Action
        >>> action = Action("some_action",
        ...     "Tag", tag=("My Company Tags", "Department", "Accounting"))
        >>> action.create()
        >>> action.delete()

    Args:
        description: Action name.
        action_type: Type of the action, value from the dropdown select.
    """
    def __init__(self, description, action_type, action_values={}, appliance=None):
        # assert action_type in self.sub_forms.keys(), "Unrecognized Action Type ({})".format(
        #     action_type)
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.action_type = action_type
        self.snapshot_name = action_values.get("snapshot_name")
        self.analysis_profile = action_values.get("analysis_profile")
        self.snapshot_age = action_values.get("snapshot_age")
        self.alerts_to_evaluate = action_values.get("alerts_to_evaluate")
        self.parent_type = action_values.get("parent_type")
        self.categories = action_values.get("categories")
        self.cpu_number = action_values.get("cpu_number")
        self.memory_amount = action_values.get("memory_amount")
        self.email_sender = action_values.get("email_sender")
        self.email_recipient = action_values.get("email_recipient")
        self.vcenter_attr_name = action_values.get("vcenter_attr_name")
        self.vcenter_attr_value = action_values.get("vcenter_attr_value")
        self.tag = action_values.get("tag")

    def __str__(self):
        return self.description

    def create(self):
        "Create this Action in UI."
        view = navigate_to(self, "Add")
        view.fill({
            "description": self.description,
            "action_type": self.action_type,
            "snapshot_name": self.snapshot_name,
            "analysis_profile": self.analysis_profile,
            "snapshot_age": self.snapshot_age,
            "alerts_to_evaluate": self.alerts_to_evaluate,
            "parent_type": self.parent_type,
            "categories": self.categories,
            "cpu_number": self.cpu_number,
            "memory_amount": self.memory_amount,
            "email_sender": self.email_sender,
            "email_recipient": self.email_recipient,
            "vcenter_attr_name": self.vcenter_attr_name,
            "vcenter_attr_value": self.vcenter_attr_value,
            "tag": self.tag
        })
        view.add_button.click()
        view = self.create_view(ActionDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Action "{}" was added'.format(self.description))

    def update(self, updates):
        """Update this Action in UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        for attr, value in updates.items():
            setattr(self, attr, value)
        view = self.create_view(ActionDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Action "{}" was saved'.format(updates.get("description", self.description)))
        else:
            view.flash.assert_message(
                'Edit of Action "{}" was cancelled by the user'.format(self.description))

    def delete(self, cancel=False):
        """Delete this Action in UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Action", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(ActionsAllView)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message('Action "{}": Delete successful'.format(self.description))

    @property
    def exists(self):
        """Check existence of this Action.

        Returns: :py:class:`bool` signalizing the presence of the Action in the database.
        """
        actions = self.appliance.db["miq_actions"]
        return self.appliance.db.session\
            .query(actions.description)\
            .filter(actions.description == self.description)\
            .count() > 0


@navigator.register(Action, "Add")
class ActionNew(CFMENavigateStep):
    VIEW = NewActionView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.actions.tree.click_path("All Actions")
        self.view.configuration.item_select("Add a new Action")


@navigator.register(Action, "Edit")
class ActionEdit(CFMENavigateStep):
    VIEW = EditActionView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.actions.tree.click_path("All Actions", self.obj.description)
        self.view.configuration.item_select("Edit this Action")


@navigator.register(Action, "Details")
class ActionDetails(CFMENavigateStep):
    VIEW = ActionDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.actions.tree.click_path("All Actions", self.obj.description)
