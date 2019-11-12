"""Page model for Control / Explorer"""
import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.control.explorer import ControlExplorerView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import CheckboxSelect
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import MultiBoxSelect
from widgetastic_manageiq import SectionedBootstrapSelect
from widgetastic_manageiq import SummaryFormItem


class ActionsAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All Actions" and
            self.actions.tree.currently_selected == ["All Actions"]
        )


class RunAnsiblePlaybookFromView(View):
    playbook_catalog_item = BootstrapSelect("service_template_id")

    @View.nested
    class inventory(View):  # noqa
        localhost = Checkbox(id="inventory_localhost")
        target_machine = Checkbox(id="inventory_event_target")
        specific_hosts = Checkbox(id="inventory_manual")
        hosts = Input(name="hosts")


class ActionFormCommon(ControlExplorerView):

    description = Input("description")
    action_type = BootstrapSelect("miq_action_type")
    snapshot_name = Input("snapshot_name")
    analysis_profile = BootstrapSelect("analysis_profile")
    alerts_to_evaluate = MultiBoxSelect()
    snapshot_age = BootstrapSelect("snapshot_age")
    parent_type = BootstrapSelect("parent_type")
    cpu_number = BootstrapSelect("cpu_value")
    memory_amount = Input("memory_value")
    email_sender = Input("from")
    email_recipient = Input("to")
    vcenter_attr_name = Input("attribute")
    vcenter_attr_value = Input("value")
    tag = VersionPicker({
        Version.lowest(): ManageIQTree("action_tags_treebox"),
        "5.11": SectionedBootstrapSelect("tag")
    })
    remove_tag = CheckboxSelect("action_options_div")
    run_ansible_playbook = View.nested(RunAnsiblePlaybookFromView)
    cancel_button = Button("Cancel")


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


@attr.s
class Action(BaseEntity, Updateable, Pretty):
    """This class represents one Action.

    Example:

        >>> from cfme.control.explorer import Action
        >>> action = Action("some_action",
        ...     action_type="Tag",
        ...     action_values={"tag": ("My Company Tags", "Service Level", "Gold")}
        >>> action.create()
        >>> action.delete()

    Args:
        description: Action name.
        action_type: Type of the action, value from the dropdown select.
    """
    description = attr.ib()
    action_type = attr.ib()
    action_values = attr.ib(default=None)

    def __attrs_post_init__(self):
        action_values = self.action_values or {}
        self.snapshot_name = action_values.get("snapshot_name")
        self.analysis_profile = action_values.get("analysis_profile")
        self.snapshot_age = action_values.get("snapshot_age")
        self._alerts_to_evaluate = action_values.get("alerts_to_evaluate")
        self.parent_type = action_values.get("parent_type")
        self.categories = action_values.get("categories")
        self.cpu_number = action_values.get("cpu_number")
        self.memory_amount = action_values.get("memory_amount")
        self.email_sender = action_values.get("email_sender")
        self.email_recipient = action_values.get("email_recipient")
        self.vcenter_attr_name = action_values.get("vcenter_attr_name")
        self.vcenter_attr_value = action_values.get("vcenter_attr_value")
        self.tag = action_values.get("tag")
        self.remove_tag = action_values.get("remove_tag")
        self.run_ansible_playbook = action_values.get("run_ansible_playbook")

    def __str__(self):
        return str(self.description)

    @cached_property
    def alerts_to_evaluate(self):
        if self._alerts_to_evaluate is not None:
            return [str(alert) for alert in self._alerts_to_evaluate]
        else:
            return self._alerts_to_evaluate

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
        view = self.create_view(ActionDetailsView, override=updates, wait='15s')
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
            view = self.create_view(ActionsAllView, wait="15s")
            view.flash.assert_success_message(
                'Action "{}": Delete successful'.format(self.description))

    @property
    def exists(self):
        """Check existence of this Action.

        Returns: :py:class:`bool` signalizing the presence of the Action in the database.
        """
        actions = self.appliance.db.client["miq_actions"]
        return self.appliance.db.client.session\
            .query(actions.description)\
            .filter(actions.description == self.description)\
            .count() > 0


@attr.s
class ActionCollection(BaseCollection):

    ENTITY = Action

    def create(self, description, action_type, action_values=None):
        """Create an Action in the UI."""
        action_values = action_values or {}
        view = navigate_to(self, "Add")
        view.fill({
            "description": description,
            "action_type": action_type,
            "snapshot_name": action_values.get("snapshot_name"),
            "analysis_profile": action_values.get("analysis_profile"),
            "snapshot_age": action_values.get("snapshot_age"),
            "alerts_to_evaluate": action_values.get("alerts_to_evaluate"),
            "parent_type": action_values.get("parent_type"),
            "categories": action_values.get("categories"),
            "cpu_number": action_values.get("cpu_number"),
            "memory_amount": action_values.get("memory_amount"),
            "email_sender": action_values.get("email_sender"),
            "email_recipient": action_values.get("email_recipient"),
            "vcenter_attr_name": action_values.get("vcenter_attr_name"),
            "vcenter_attr_value": action_values.get("vcenter_attr_value"),
            "tag": action_values.get("tag"),
            "remove_tag": action_values.get("remove_tag"),
            "run_ansible_playbook": action_values.get("run_ansible_playbook")
        })
        # todo: check whether we can remove ensure_page_safe later
        self.browser.plugin.ensure_page_safe()
        view.add_button.click()
        action = self.instantiate(description, action_type, action_values=action_values)
        view = action.create_view(ActionDetailsView, wait='10s')
        view.flash.assert_success_message('Action "{}" was added'.format(action.description))
        return action


@navigator.register(ActionCollection, "All")
class ActionsAll(CFMENavigateStep):
    VIEW = ActionsAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self, *args, **kwargs):
        self.prerequisite_view.actions.tree.click_path("All Actions")


@navigator.register(ActionCollection, "Add")
class ActionNew(CFMENavigateStep):
    VIEW = NewActionView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Add a new Action")


@navigator.register(Action, "Edit")
class ActionEdit(CFMENavigateStep):
    VIEW = EditActionView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Action")


@navigator.register(Action, "Details")
class ActionDetails(CFMENavigateStep):
    VIEW = ActionDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.actions.tree.click_path("All Actions", self.obj.description)
