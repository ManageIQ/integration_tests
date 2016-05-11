# -*- coding: utf-8 -*-
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTree, Table, flash, form_buttons, mixins, toolbar
from utils import version

pol_btn = partial(toolbar.select, "Policy")


class PolicyProfileAssignable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign Policy Profiles"""
    manage_policies_tree = CheckboxTree("//div[@id='protect_treebox']/ul")

    @property
    def assigned_policy_profiles(self):
        try:
            return self._assigned_policy_profiles
        except AttributeError:
            self._assigned_policy_profiles = set([])
            return self._assigned_policy_profiles

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        map(self.assigned_policy_profiles.add, policy_profile_names)
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        for pp_name in policy_profile_names:
            try:
                self.assigned_policy_profiles.remove(pp_name)
            except KeyError:
                pass
        self._assign_unassign_policy_profiles(False, *policy_profile_names)

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Wheter to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
        """
        self.load_details(refresh=True)
        pol_btn("Manage Policies")
        for policy_profile in policy_profile_names:
            if assign:
                self.manage_policies_tree.check_node(policy_profile)
            else:
                self.manage_policies_tree.uncheck_node(policy_profile)
        sel.move_to_element({
            version.LOWEST: '#tP',
            "5.5": "//h3[1]"})
        form_buttons.save()
        flash.assert_no_errors()


class Taggable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign tags."""
    def add_tag(self, tag, single_value=False):
        self.load_details(refresh=True)
        mixins.add_tag(tag, single_value=single_value, navigate=True)

    def remove_tag(self, tag):
        self.load_details(refresh=True)
        mixins.remove_tag(tag)

    def get_tags(self, tag="My Company Tags"):
        self.load_details(refresh=True)
        return mixins.get_tags(tag=tag)


class Validatable(object):
    """
    Class which Middleware provider and other middleware pages must extend
    to be able to validate properties values shown in summary page.

    """

    """
    Tuples which first value is the provider class's attribute name,
    the second value is provider's UI summary page field key.

    Should have values in child classes.

    """
    property_tuples = []

    def properties_ui(self):
        self.load_details(refresh=True)
        property_ui = {}
        for row in Table('//div[@id="main-content"]//table').rows():
            property_ui[row[0].text] = row[1].text
        return property_ui

    def validate_properties(self):
        """
        Validation method which checks whether class attributes,
        which were used during creation of provider,
        is correctly displayed in Properties section of provider UI.
        The maps between class attribute and UI property is done via 'property_tuples' variable.

        Fails if some property does not match.
        """
        properties = self.properties_ui()
        assert len(properties) > 0, 'No property was found in UI'
        for property_tuple in self.property_tuples:
            expected_value = str(getattr(self, property_tuple[0]))
            shown_value = str(properties[property_tuple[1]])
            assert(expected_value == shown_value,
                   'Property {} has wrong value, expected {} but was {}'
                   .format(property_tuple[1], expected_value, shown_value))
