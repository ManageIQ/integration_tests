# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import TextInput
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
from widgetastic_manageiq import MultiBoxSelect


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
            self.title.text == "Adding a new Policy Profile" and
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
    entities = Table(".//div[@id='main_div']/table")

    @property
    def is_displayed(self):

        return (
            self.in_control_explorer and
            # BZ(1516302)
            'All Policy Profile' in self.title.text
        )


@attr.s
class PolicyProfile(BaseEntity, Updateable, Pretty):

    description = attr.ib()
    policies = attr.ib()
    notes = attr.ib(default=None)

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
        view = self.create_view(PolicyProfileDetailsView, override=updates, wait='10s')
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


@attr.s
class PolicyProfileCollection(BaseCollection):

    ENTITY = PolicyProfile

    def create(self, description, policies, notes=None):
        policy_profile = self.instantiate(description, policies, notes=notes)
        view = navigate_to(self, "Add")
        view.fill({
            "description": policy_profile.description,
            "notes": policy_profile.notes,
            "policies": [policy.name_for_policy_profile for policy in policy_profile.policies]
        })
        view.add_button.click()
        view = policy_profile.create_view(PolicyProfileDetailsView)
        assert view.is_displayed
        view.flash.assert_success_message('Policy Profile "{}" was added'.format(
            policy_profile.description))
        return policy_profile

    @property
    def all_policy_profile_names(self):
        view = navigate_to(self, "All")
        return [row[1].text for row in view.entities]


@navigator.register(PolicyProfileCollection, "All")
class PolicyProfileAll(CFMENavigateStep):
    VIEW = PolicyProfilesAllView
    prerequisite = NavigateToAttribute("appliance.server", "ControlExplorer")

    def step(self, *args, **kwargs):
        self.prerequisite_view.policy_profiles.tree.click_path("All Policy Profiles")


@navigator.register(PolicyProfileCollection, "Add")
class PolicyProfileNew(CFMENavigateStep):
    VIEW = NewPolicyProfileView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Add a New Policy Profile")


@navigator.register(PolicyProfile, "Edit")
class PolicyProfileEdit(CFMENavigateStep):
    VIEW = EditPolicyProfileView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Policy Profile")


@navigator.register(PolicyProfile, "Details")
class PolicyProfileDetails(CFMENavigateStep):
    VIEW = PolicyProfileDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.policy_profiles.tree.click_path(
            "All Policy Profiles",
            self.obj.description
        )
