# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import CheckableBootstrapTreeview as CbTree
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
from cfme.utils.wait import wait_for
from widgetastic_manageiq import MultiBoxSelect


class AlertProfileFormCommon(ControlExplorerView):
    title = Text("#explorer_title_text")

    description = Input(name="description")
    notes = TextInput(name="notes")
    alerts = MultiBoxSelect()

    cancel_button = Button("Cancel")


class NewAlertProfileView(AlertProfileFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "Adding a new Alert Profile" and
            self.alert_profiles.tree.currently_selected == [
                "All Alert Profiles",
                "{} Alert Profiles".format(self.context["object"].TYPE)
            ]
        )


class EditAlertProfileView(AlertProfileFormCommon):
    save_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Editing {} Alert Profile "{}"'.format(
                self.context["object"].TYPE,
                self.context["object"].description) and
            self.alert_profiles.tree.currently_selected == [
                "All Alert Profiles",
                "{} Alert Profiles".format(self.context["object"].TYPE),
                self.context["object"].description
            ]
        )


class AlertProfileDetailsView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Alert Profile "{}"'.format(self.context["object"].description)
        )


class AlertProfilesAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All Alert Profiles"
        )


class AlertProfilesEditAssignmentsView(ControlExplorerView):
    title = Text("#explorer_title_text")
    assign_to = BootstrapSelect("chosen_assign_to")
    tag_category = BootstrapSelect("chosen_cat")
    selections = CbTree("object_treebox")
    header = Text("//div[@id='alert_profile_assign_div']/h3")
    based_on = Text('//label[normalize-space(.)="Based On"]/../div')

    save_button = Button("Save")
    reset_button = Button("Reset")
    cancel_button = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Alert Profile "{}"'.format(self.context["object"].description) and
            self.header.text == "Assignments" and
            self.based_on.text == self.context["object"].TYPE
        )


@attr.s
class BaseAlertProfile(BaseEntity, Updateable, Pretty):

    TYPE = None
    _param_name = ParamClassName('description')
    pretty_attrs = ["description", "alerts"]

    description = attr.ib()
    alerts = attr.ib(default=None)
    notes = attr.ib(default=None)

    def update(self, updates):
        """Update this Alert Profile in UI.

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
        for attrib, value in updates.items():
            setattr(self, attrib, value)
        view = self.create_view(AlertProfileDetailsView)
        wait_for(lambda: view.is_displayed, timeout=10,
            message="wait AlertProfileDetailsView is displayed")
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Alert Profile "{}" was saved'.format(
                    updates.get("description", self.description)))
        else:
            view.flash.assert_message(
                'Edit of Alert Profile "{}" was cancelled by the user'.format(self.description))

    def delete(self, cancel=False):
        """Delete this Alert Profile in UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select("Delete this Alert Profile", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
        view.flash.assert_no_error()

    @property
    def exists(self):
        """Check existence of this Alert Profile.

        Returns: :py:class:`bool` signalizing the presence of the Alert Profile in database.
        """
        miq_sets = self.appliance.db.client["miq_sets"]
        return self.appliance.db.client.session\
            .query(miq_sets.description)\
            .filter(
                miq_sets.description == self.description and miq_sets.set_type == "MiqAlertSet")\
            .count() > 0

    def assign_to(self, assign, selections=None, tag_category=None):
        """Assigns this Alert Profile to specified objects.

        Args:
            assign: Where to assign (The Enterprise, ...).
            selections: What items to check in the tree. N/A for The Enteprise.
            tag_category: Only for choices starting with Tagged. N/A for The Enterprise.

        Returns:
            Boolean indicating if assignment was made (form fill changed)
        """
        view = navigate_to(self, "Edit assignments")
        changed = []
        if selections is not None:
            selections = view.selections.CheckNode(selections)
        changed = view.fill({
            "assign_to": assign,
            "tag_category": tag_category,
            "selections": selections
        })
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(AlertProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        return changed


@attr.s
class AlertProfileCollection(BaseCollection):

    def instantiate(self, *args, **kwargs):
        alert_profile_class = args[0]
        args = args[1:]
        return alert_profile_class.from_collection(self, *args, **kwargs)

    def create(self, alert_profile_class, description, alerts=None, notes=None):
        alert_profile = self.instantiate(alert_profile_class, description, alerts=alerts,
            notes=notes)
        view = navigate_to(alert_profile, "Add")
        view.fill({
            "description": alert_profile.description,
            "notes": alert_profile.notes,
            "alerts": [str(alert) for alert in alert_profile.alerts]
        })
        view.add_button.click()
        view = alert_profile.create_view(AlertProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message(
            'Alert Profile "{}" was added'.format(alert_profile.description))
        return alert_profile


@navigator.register(AlertProfileCollection, "All")
class AlertProfilesAll(CFMENavigateStep):
    VIEW = AlertProfilesAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self, *args, **kwargs):
        self.prerequisite_view.alert_profiles.tree.click_path("All Alert Profiles")


@navigator.register(BaseAlertProfile, "Add")
class AlertProfileNew(CFMENavigateStep):
    VIEW = NewAlertProfileView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.alert_profiles.tree.click_path("All Alert Profiles",
            "{} Alert Profiles".format(self.obj.TYPE))
        self.prerequisite_view.configuration.item_select(
            "Add a New {} Alert Profile".format(self.obj.TYPE))


@navigator.register(BaseAlertProfile, "Edit")
class AlertProfileEdit(CFMENavigateStep):
    VIEW = EditAlertProfileView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Alert Profile")


@navigator.register(BaseAlertProfile, "Edit assignments")
class AlertProfileEditAssignments(CFMENavigateStep):
    VIEW = AlertProfilesEditAssignmentsView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit assignments for this Alert Profile")


@navigator.register(BaseAlertProfile, "Details")
class AlertProfileDetails(CFMENavigateStep):
    VIEW = AlertProfileDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.alert_profiles.tree.click_path("All Alert Profiles",
            "{} Alert Profiles".format(self.obj.TYPE), self.obj.description)


class ClusterAlertProfile(BaseAlertProfile):
    TYPE = "Cluster / Deployment Role"


class DatastoreAlertProfile(BaseAlertProfile):
    TYPE = "Datastore"


class HostAlertProfile(BaseAlertProfile):
    TYPE = "Host / Node"


class ProviderAlertProfile(BaseAlertProfile):
    TYPE = "Provider"


class ServerAlertProfile(BaseAlertProfile):
    TYPE = "Server"


class VMInstanceAlertProfile(BaseAlertProfile):
    TYPE = "VM and Instance"


class NodeAlertProfile(BaseAlertProfile):
    TYPE = "Container Node"
