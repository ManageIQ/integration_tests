# -*- coding: utf-8 -*-
from cached_property import cached_property
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, TextInput
from widgetastic_manageiq import MultiBoxSelect
from widgetastic_patternfly import Button, Input

from . import ControlExplorerView
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


class PolicyProfileFormCommon(ControlExplorerView):
    title = Text("#explorer_title_text")

    description = Input(name="description")
    notes = TextInput(name="notes")
    policies = MultiBoxSelect()
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


class PolicyProfileCollection(NavigatableMixin):

    def __init__(self, appliance):
        self.appliance = appliance

    def instantiate(self, description, collection, policies_to_assign=None, notes=None):
        return PolicyProfile(description, self, policies_to_assign=policies_to_assign, notes=notes)

    def create(self, description, policies_to_assign=None, notes=None):
        policy = self.instantiate(description, self, policies_to_assign=policies_to_assign, notes=notes)
        view = navigate_to(self, "Add")
        view.fill({
            "description": policy.description,
            "notes": policy.notes,
            "policies": policy.prepared_policies
        })
        view.add_button.click()
        view = policy.create_view(PolicyProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message('Policy Profile "{}" was added'.format(
            policy.description))
        return policy


class PolicyProfile(Updateable, NavigatableMixin, Pretty):

    def __init__(self, description, collection, policies_to_assign=None, notes=None):
        self.collection = collection
        self.appliance = self.collection.appliance
        self.description = description
        self.notes = notes
        self.policies_to_assign = policies_to_assign

    @property
    def parent(self):
        return self.collection

    @property
    def policy_profile(self):
        return self

    @cached_property
    def policies(self):
        from .policies import PolicyCollection
        return PolicyCollection(self)

    @property
    def prepared_policies(self):
        if self.policies_to_assign is not None:
            return ["{} {}: {}".format(policy.PRETTY, policy.TYPE, policy.description) for
                    policy in self.policies_to_assign]
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
        view = self.create_view(PolicyProfileDetailsView, override=updates)
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
            view.flash.assert_success_message(
                'Policy Profile "{}": Delete successful'.format(self.description))

    @property
    def exists(self):
        """Check existence of this Policy Profile.

        Returns: :py:class:`bool` signalizing the presence of the Policy Profile in database.
        """
        miq_sets = self.appliance.db.client["miq_sets"]
        return self.appliance.db.client.session\
            .query(miq_sets.description)\
            .filter(
                miq_sets.description == self.description and miq_sets.set_type == "MiqPolicySet")\
            .count() > 0


@navigator.register(PolicyProfileCollection, "All")
class PolicyProfileAll(CFMENavigateStep):
    VIEW = PolicyProfilesAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.prerequisite_view.policy_profiles.tree.click_path("All Policy Profiles")


@navigator.register(PolicyProfileCollection, "Add")
class PolicyProfileNew(CFMENavigateStep):
    VIEW = NewPolicyProfileView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a New Policy Profile")


@navigator.register(PolicyProfile, "Edit")
class PolicyProfileEdit(CFMENavigateStep):
    VIEW = EditPolicyProfileView
    prerequisite = NavigateToSibling("Details") 

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Policy Profile")


@navigator.register(PolicyProfile, "Details")
class PolicyProfileDetails(CFMENavigateStep):
    VIEW = PolicyProfileDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self):
        self.prerequisite_view.policy_profiles.tree.click_path(
            "All Policy Profiles",
            self.obj.description
        )
