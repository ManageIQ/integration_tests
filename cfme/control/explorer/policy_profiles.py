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


class PolicyProfileFormCommon(ControlExplorerView):
    title = Text("#explorer_title_text")

    description = Input(name="description")
    notes = TextInput(name="notes")
    policies = MultiBoxSelect(
        "formtest",
        move_into=".//a[@data-submit='choices_chosen_div']/img",
        move_from=".//a[@data-submit='members_chosen_div']/img"
    )

    cancel_button = Button("Cancel")


class NewPolicyProfileView(PolicyProfileFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "Adding a New Policy Profile" and
            self.policy_profiles.tree.currently_selected == ["All Policy Profiles"]
        )


class EditPolicyProfileView(PolicyProfileFormCommon):
    save_button = Button("Save")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Editing Policy Profile "{}"'.format(
                self.context["object"].description) and
            self.policy_profiles.tree.currently_selected == [
                "All Policy Profiles",
                self.context["object"].description
            ]
        )


class PolicyProfileDetailsView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == 'Policy Profile "{}"'.format(self.context["object"].description)
        )


class PolicyProfilesAllView(ControlExplorerView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_control_explorer and
            self.title.text == "All Policy Profiles"
        )


class PolicyProfile(Updateable, Navigatable, Pretty):

    def __init__(self, description, policies=None, notes=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.notes = notes
        self.policies = policies

    def create(self):
        view = navigate_to(self, "Add")
        view.fill({
            "description": self.description,
            "notes": self.notes,
            "policies": self.prepared_policies
        })
        view.add_button.click()
        view = self.create_view(PolicyProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Policy Profile "{}" was added'.format(self.description))

    @property
    def prepared_policies(self):
        if self.policies is not None:
            return ["{} {}: {}".format(
                policy.PRETTY, policy.TYPE, policy.description) for policy in self.policies]
        else:
            return None

    def update(self, updates):
        """Update this Policy Profile in UI.

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
        view = self.create_view(PolicyProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(
                'Policy Profile "{}" was saved'.format(
                    updates.get("description", self.description)))
        else:
            view.flash.assert_message(
                'Edit of Policy Profile "{}" was cancelled by the user'.format(self.description))

    def delete(self, cancel=False):
        """Delete this Policy Profile in UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove this Policy Profile", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(PolicyProfilesAllView)
            assert view.is_displayed
            view.flash.assert_no_error()
            view.flash.assert_message(
                'Policy Profile "{}": Delete successful'.format(self.description))

    @property
    def exists(self):
        """Check existence of this Policy Profile.

        Returns: :py:class:`bool` signalizing the presence of the Policy Profile in database.
        """
        miq_sets = self.appliance.db["miq_sets"]
        return self.appliance.db.session\
            .query(miq_sets.description)\
            .filter(
                miq_sets.description == self.description and miq_sets.set_type == "MiqPolicySet")\
            .count() > 0


@navigator.register(PolicyProfile, "Add")
class PolicyProfileNew(CFMENavigateStep):
    VIEW = NewPolicyProfileView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.policy_profiles.tree.click_path("All Policy Profiles")
        self.view.configuration.item_select("Add a New Policy Profile")


@navigator.register(PolicyProfile, "Edit")
class PolicyProfileEdit(CFMENavigateStep):
    VIEW = EditPolicyProfileView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.policy_profiles.tree.click_path("All Policy Profiles", self.obj.description)
        self.view.configuration.item_select("Edit this Policy Profile")


@navigator.register(PolicyProfile, "Details")
class PolicyProfileDetails(CFMENavigateStep):
    VIEW = PolicyProfileDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.view.policy_profiles.tree.click_path("All Policy Profiles", self.obj.description)
