# -*- coding: utf-8 -*-
from utils.pretty import Pretty
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from navmazing import NavigateToAttribute

from widgetastic.widget import Text, TextInput
from widgetastic_manageiq import MultiBoxSelect
from widgetastic_patternfly import Button, Input

from . import ControlExplorerView
from utils.appliance import Navigatable
from utils.update import Updateable


class AlertProfileFormCommon(ControlExplorerView):
    title = Text("#explorer_title_text")

    description = Input(name="description")
    notes = TextInput(name="notes")
    alerts = MultiBoxSelect(
        "formtest",
        move_into=".//a[@data-submit='choices_chosen_div']/img",
        move_from=".//a[@data-submit='members_chosen_div']/img"
    )

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
            self.title.text == "All {} Alert Profiles".format(self.context["object"].TYPE)
        )


class BaseAlertProfile(Updateable, Navigatable, Pretty):

    TYPE = None

    def __init__(self, description, alerts=None, notes=None, appliance=None):
            Navigatable.__init__(self, appliance=appliance)
            self.description = description
            self.notes = notes
            self.alerts = alerts

    def create(self):
        view = navigate_to(self, "Add")
        view.fill({
            "description": self.description,
            "notes": self.notes,
            "alerts": [str(alert) for alert in self.alerts]
        })
        view.add_button.click()
        view = self.create_view(AlertProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Alert Profile "{}" was added'.format(self.description))

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
        for attr, value in updates.items():
            setattr(self, attr, value)
        view = self.create_view(AlertProfileDetailsView)
        assert view.is_displayed
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
        else:
            view = self.create_view(AlertProfilesAllView)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message(
                'Alert Profile "{}": Delete successful'.format(self.description))

    @property
    def exists(self):
        """Check existence of this Alert Profile.

        Returns: :py:class:`bool` signalizing the presence of the Alert Profile in the database.
        """
        miq_sets = self.appliance.db["miq_sets"]
        return self.appliance.db.session.query(miq_sets.description)\
            .filter(
                miq_sets.description == self.description and miq_sets.set_type == "MiqAlertSet")\
            .count() > 0


@navigator.register(BaseAlertProfile, "Add")
class AlertProfileNew(CFMENavigateStep):
    VIEW = NewAlertProfileView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alert_profiles.tree.click_path("All Alert Profiles",
            "{} Alert Profiles".format(self.obj.TYPE))
        self.view.configuration.item_select("Add a New {} Alert Profile".format(self.obj.TYPE))


@navigator.register(BaseAlertProfile, "Edit")
class AlertProfileEdit(CFMENavigateStep):
    VIEW = EditAlertProfileView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alert_profiles.tree.click_path("All Alert Profiles",
            "{} Alert Profiles".format(self.obj.TYPE), self.obj.description)
        self.view.configuration.item_select("Edit this Alert Profile")


@navigator.register(BaseAlertProfile, "Details")
class AlertProfileDetails(CFMENavigateStep):
    VIEW = AlertProfileDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.alert_profiles.tree.click_path("All Alert Profiles",
            "{} Alert Profiles".format(self.obj.TYPE), self.obj.description)


class ClusterAlertProfile(BaseAlertProfile):

    TYPE = "Cluster / Deployment Role"


class DatastoreAlertProfile(BaseAlertProfile):

    TYPE = "Datastore"


class HostAlertProfile(BaseAlertProfile):

    TYPE = "Host / Node"


class MiddlewareServerAlertProfile(BaseAlertProfile):

    TYPE = "Middleware Server"


class ProviderAlertProfile(BaseAlertProfile):

    TYPE = "Provider"


class ServerAlertProfile(BaseAlertProfile):

    TYPE = "Server"


class VMInstanceAlertProfile(BaseAlertProfile):

    TYPE = "VM and Instance"
