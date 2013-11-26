# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
from pages.control_subpages.explorer import Explorer
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.taskbar.taskbar import TaskbarMixin
from pages.regions.expression_editor_mixin import ExpressionEditorMixin
from pages.regions.refresh_mixin import RefreshMixin
import re


class Policies(Explorer):
    """ Control / Explorer / Policies

    """

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _configuration_add_new_locator = (By.CSS_SELECTOR,
                                      "tr[title*='Add a New']")

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_add_new_button(self):
        return self.selenium.find_element(*self._configuration_add_new_locator)

    def go(self, typename, name, continuation):
        """ DRY function to find something in the tree, click it and direct
        to the correct page.

        @param typename: What we are looking for? (Policy, Condition, ...)
                         Used for throwing exceptions
        @param name: Name of the node
        @param continuation: Class of the page to instantiate
        @type continuation: subclass of Page
        """
        node = self.accordion.current_content.get_node(name)
        try:
            node.click()
        except AttributeError:
            raise Exception("%s '%s' not found!" % (typename, name))
        self._wait_for_results_refresh()
        return continuation(self.testsetup)

    def _new_policy(self, where):
        """ DRY method that takes the location in the tree and goes there.

        @return: NewPolicy
        """
        self.accordion.current_content.get_node(where).click()
        self._wait_for_results_refresh()
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_add_new_button)\
            .perform()
        self._wait_for_results_refresh()
        return NewPolicy(self.testsetup)

    def select_host_control_policy(self, policy):
        """ Selects policy by its name

        @return: PolicyView
        """
        path = "Control Policies/Host Control Policies::%s" % policy
        return self.go("Policy", path, PolicyView)

    def add_new_host_control_policy(self):
        """ Goes to the page with editor of new policy

        @return: NewPolicy
        """
        return self._new_policy("Control Policies::Host Control Policies")

    def select_vm_control_policy(self, policy):
        """ Selects policy by its name

        @return: PolicyView
        """
        path = "Control Policies/Vm Control Policies::%s" % policy
        return self.go("Policy", path, PolicyView)

    def add_new_vm_control_policy(self):
        """ Goes to the page with editor of new policy

        @return: NewPolicy
        """
        return self._new_policy("Control Policies::Vm Control Policies")

    def select_host_compliance_policy(self, policy):
        """ Selects policy by its name

        @return: PolicyView
        """
        path = "Control Policies/Host Compliance Policies::%s" % policy
        return self.go("Policy", path, PolicyView)

    def add_new_host_compliance_policy(self):
        """ Goes to the page with editor of new policy

        @return: NewPolicy
        """
        return self._new_policy("Compliance Policies::Host Compliance Policies")

    def select_vm_compliance_policy(self, policy):
        """ Selects policy by its name

        @return: PolicyView
        """
        path = "Control Policies/Vm Compliance Policies::%s" % policy
        return self.go("Policy", path, PolicyView)

    def add_new_vm_compliance_policy(self):
        """ Goes to the page with editor of new policy

        @return: NewPolicy
        """
        return self._new_policy("Compliance Policies::Vm Compliance Policies")


class PolicyView(Policies, TaskbarMixin, RefreshMixin):
    """ This page represents the view on the policy with its details

    @todo: Delete policy. I cannot delete a policy now so I will have to check it.
    """
    _info_active_locator = (By.XPATH,
                            "//*[@id=\"policy_info_div\"]/fieldset[1]/table/tbody/tr[1]/td[2]")
    _info_created_locator = (By.XPATH,
                             "//*[@id=\"policy_info_div\"]/fieldset[1]/table/tbody/tr[2]/td[2]")
    _info_updated_locator = (By.XPATH,
                             "//*[@id=\"policy_info_div\"]/fieldset[1]/table/tbody/tr[3]/td[2]")
    _notes_field_locator = (By.CSS_SELECTOR, "textarea#notes")
    _scope_fieldset_locator = (By.XPATH, "//*[@id=\"policy_info_div\"]/fieldset[2]")
    _conditions_table_locator = (By.XPATH, "//*[@id=\"policy_info_div\"]/fieldset[3]/table/tbody")
    _events_table_locator = (By.XPATH, "//*[@id=\"policy_info_div\"]/fieldset[4]/table/tbody")
    _profiles_belongs_locator = (By.XPATH, "//*[@id=\"policy_info_div\"]/fieldset[6]/table/tbody")

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _configuration_edit_basic_locator = (By.CSS_SELECTOR,
                                         "tr[title='Edit Basic Info, Scope, and Notes']")
    _configuration_new_condition_locator = (By.CSS_SELECTOR,
            "tr[title='Create a new Condition assigned to this Policy']")
    _configuration_edit_policy_condition_assignment_locator = (By.CSS_SELECTOR,
            "tr[title='Edit this Policy\\'s Condition assignments']")
    _configuration_edit_policy_event_locator = (By.CSS_SELECTOR,
            "tr[title='Edit this Policy\\'s Event assignments']")

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_edit_basic_button(self):
        return self.selenium.find_element(*self._configuration_edit_basic_locator)

    @property
    def configuration_new_condition_button(self):
        return self.selenium.find_element(*self._configuration_new_condition_locator)

    @property
    def configuration_edit_policy_condition_assignment_button(self):
        return self.selenium\
                   .find_element(*self._configuration_edit_policy_condition_assignment_locator)

    @property
    def configuration_edit_policy_event_assignment_button(self):
        return self.selenium\
                   .find_element(*self._configuration_edit_policy_event_assignment_locator)

    def edit_basic(self):
        """ Fire up the basic editing page

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_edit_basic_button)\
            .perform()
        self._wait_for_results_refresh()
        return BasicEditPolicy(self.testsetup)

    def new_condition(self):
        """ Fire up the new condition editing page

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_new_condition_button)\
            .perform()
        self._wait_for_results_refresh()
        return NewConditionForPolicy(self.testsetup)

    def edit_policy_condition_assignments(self):
        """ Fire up the policy condition assignments editing page

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_edit_policy_condition_assignment_button)\
            .perform()
        self._wait_for_results_refresh()
        return PolicyConditionAssignments(self.testsetup)

    def edit_policy_event_assignments(self):
        """ Fire up the policy event assignments editing page

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_edit_policy_event_assignment_button)\
            .perform()
        self._wait_for_results_refresh()
        return PolicyEventAssignments(self.testsetup)

    @property
    def active(self):
        text = self.selenium.find_element(*self._info_active_locator).text.strip().lower()
        return text == "yes"

    @property
    def created(self):
        return self.selenium.find_element(*self._info_created_locator).text.strip()

    @property
    def updated(self):
        return self.selenium.find_element(*self._info_updated_locator).text.strip()

    @property
    def notes(self):
        node = self.selenium.find_element(*self._notes_field_locator)
        if not node:
            return None
        return node.text.strip()

    @property
    def scope(self):
        node = self.selenium.find_element(*self._scope_fieldset_locator)
        # It contains also the caption, so we need to cut it out
        return node.text.strip().split(":", 1)[-1].lstrip()

    @property
    def list_conditions(self):
        """ Return all conditions belonging to this policy

        """
        node = self.selenium.find_element(*self._conditions_table_locator)
        if not node:
            return []
        conds = []
        for row in node.find_elements_by_css_selector("tr"):
            icon, description, scopes = row.find_elements_by_css_selector("td")
            conds.append((description, scopes))
        return conds

    def go_to_condition(self, condition_name):
        """ Search condition and click on it

        This cycles through all the table of condition and searches for the sought one.
        When found, it clicks on it and returns its view.

        @return: PolicyConditionView
        @raise: Exception when not found
        """
        present = []
        for condition, scopes in self.list_conditions:
            if condition.text.strip() == condition_name.strip():
                condition.click()
                self._wait_for_results_refresh()
                return PolicyConditionView(self.testsetup)
            present.append(condition.text.strip())
        raise Exception("Condition with description %s was not found (%s present)" %
            (condition_name, ", ".join(present))
        )

    @property
    def list_events(self):
        """ Return all events belonging to this policy

        """
        node = self.selenium.find_element(*self._events_table_locator)
        if not node:
            return []
        conds = []
        for row in node.find_elements_by_xpath("./tr"):
            icon, event, actions = row.find_elements_by_xpath("./td")
            conds.append((event, actions.find_elements_by_css_selector("tr")))
        return conds

    def go_to_event(self, event_name):
        """ Search event and click on it

        This cycles through all the table of events and searches for the sought one.
        When found, it clicks on it and returns its view.

        @return: PolicyEventView
        @raise: Exception when not found
        """
        present = []
        for event, actions in self.list_events:
            if event.text.strip() == event_name.strip():
                event.click()
                self._wait_for_results_refresh()
                return PolicyEventView(self.testsetup)
            present.append(event.text.strip())
        raise Exception("Event with name %s was not found (%s present)" %
            (event_name, ", ".join(present))
        )

    @property
    def list_profiles(self):
        """ Return all profiles belonging to this policy

        @todo: Transition to the profile page?

        """
        node = self.selenium.find_element(*self._profiles_belongs_locator)
        if not node:
            return []
        profs = []
        for row in node.find_elements_by_css_selector("tr"):
            icon, description = row.find_elements_by_css_selector("td")
            profs.append(description)
        return profs

    @property
    def list_profiles_text(self):
        """ Return all profiles belonging to this policy in text

        """
        return [p.text.strip() for p in self.list_profiles]

    def set_assigned_events(self, policies):
        """ Shortcut to set the assigned events from dictionary.

        You must accept the returning value to make the object behave correctly.
        Example:

        policy = policy.set_assigned_events({"foo": True})

        """
        return self.edit_policy_event_assignments()\
                   .mass_set(policies)\
                   .save()


class EditPolicy(Policies, ExpressionEditorMixin):
    """ First editing type of the policy.

    Configuration / Edit Basic Info ....

    Test example:

    edit_policy = pg_policies.select_policy("tag_complete").edit_basic()
    edit_policy.delete_all_expressions()
    edit_policy.select_first_expression()   # Actually not needed as the ??? is selected
                                            # when no expression is present
    edit_policy.fill_expression_field(
        "VM and Instance : CPU - Moderate Recommendation",
        "RUBY",
        "puts \"olol\""
    )
    edit_policy.commit_expression()
    edit_policy.notes = "hello"
    edit_policy.select_expression_by_text("Moderate Recommendation")
    edit_policy.NOT_expression()
    edit_policy.select_expression_by_text("Moderate Recommendation")
    edit_policy.AND_expression()
    edit_policy.fill_expression_count(
        "VM and Instance.Hardware.Partitions",
        "=",
        "3"
    )
    edit_policy.commit_expression()
    edit_policy.select_expression_by_text("Partitions")
    edit_policy.OR_expression()
    edit_policy.discard_expression()
    policies = edit_policy.save()
    assert "hello" in policies.notes

    """
    _description_input_locator = (By.CSS_SELECTOR, "input#description")
    _active_checkbox_locator = (By.CSS_SELECTOR, "input#active")
    _notes_textarea_locator = (By.CSS_SELECTOR, "textarea#notes")

    @property
    def description_input(self):
        return self.selenium.find_element(*self._description_input_locator)

    @property
    def active_checkbox(self):
        return self.selenium.find_element(*self._active_checkbox_locator)

    @property
    def notes_textarea(self):
        return self.selenium.find_element(*self._notes_textarea_locator)

    @property
    def is_active(self):
        """ Checks whether this policy is active.

        """
        return self.active_checkbox.is_selected()

    def activate(self):
        """ Activate this policy.

        """
        if not self.is_active:
            self.active_checkbox.click()

    def deactivate(self):
        """ Deactivate this policy.

        """
        if self.is_active:
            self.active_checkbox.click()

    @property
    def notes(self):
        """ Returns contents of the notes textarea

        """
        return self.notes_textarea.text.strip()

    @notes.setter
    def notes(self, value):
        """ Sets the contents of the notes textarea

        """
        self.fill_field_element(value, self.notes_textarea)

    @property
    def description(self):
        """ Returns description

        """
        return self.description_input.get_attribute("value").strip()

    @description.setter
    def description(self, value):
        """ Sets description

        """
        self.fill_field_element(value, self.description_input)


class BasicEditPolicy(EditPolicy):
    _save_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    @property
    def save_button(self):
        return self.selenium.find_element(*self._save_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_locator)

    @property
    def reset_button(self):
        return self.selenium.find_element(*self._reset_locator)

    def save(self):
        """ Save changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=10)
        self.save_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._cancel_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def reset(self):
        """ Reset changes.

        Stays on the page.
        @return: True if the flash message shows correct message.
        @rtype: bool
        """
        self._wait_for_visible_element(*self._reset_locator, visible_timeout=10)
        self.reset_button.click()
        self._wait_for_results_refresh()
        return "All changes have been reset" in self.flash.message


class NewPolicy(EditPolicy):
    _add_locator = (By.CSS_SELECTOR, "img[title='Add']")
    _cancel_locator = (By.CSS_SELECTOR, "img[title='Cancel']")

    @property
    def add_button(self):
        return self.selenium.find_element(*self._add_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_locator)

    def add(self):
        """ Save changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._add_locator, visible_timeout=10)
        self.add_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._cancel_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return Policies(self.testsetup)


class BaseConditionForPolicy(Policies, ExpressionEditorMixin):
    """ General editing class, used for inheriting

    """
    _edit_this_expression_locator = (By.CSS_SELECTOR,
                                     "#form_expression_div img[alt='Edit this Expression']")
    _edit_this_scope_locator = (By.CSS_SELECTOR, "#form_scope_div img[alt='Edit this Scope']")

    _description_input_locator = (By.CSS_SELECTOR, "input#description")
    _notes_textarea_locator = (By.CSS_SELECTOR, "textarea#notes")

    @property
    def add_button(self):
        return self.selenium.find_element(*self._add_button_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_button_locator)

    @property
    def description_input(self):
        return self.selenium.find_element(*self._description_input_locator)

    @property
    def notes_textarea(self):
        return self.selenium.find_element(*self._notes_textarea_locator)

    @property
    def edit_expression_button(self):
        return self.selenium.find_element(*self._edit_this_expression_locator)

    @property
    def edit_scope_button(self):
        return self.selenium.find_element(*self._edit_this_scope_locator)

    @property
    def is_editing_expression(self):
        return not self.is_element_visible(*self._edit_this_expression_locator)

    @property
    def is_editing_scope(self):
        return not self.is_element_visible(*self._edit_this_scope_locator)

    def edit_expression(self):
        """ Switches the editing of the Expression on.

        """
        if not self.is_editing_expression:
            self.edit_expression_button.click()
            self._wait_for_results_refresh()

    def edit_scope(self):
        """ Switches the editing of the Scope on.

        """
        if not self.is_editing_scope:
            self.edit_scope_button.click()
            self._wait_for_results_refresh()

    @property
    def notes(self):
        """ Returns contents of the notes textarea

        """
        return self.notes_textarea.text.strip()

    @notes.setter
    def notes(self, value):
        """ Sets the contents of the notes textarea

        """
        self.notes_textarea.clear()
        self.notes_textarea.send_keys(value)

    @property
    def description(self):
        """ Returns description

        """
        return self.description_input.get_attribute("value").strip()

    @description.setter
    def description(self, value):
        """ Sets description

        """
        self.description_input.clear()
        self.description_input.send_keys(value)


class NewConditionForPolicy(BaseConditionForPolicy):
    """ Page representing an editation of the new Condition

    Inherits and adds two buttons.

    """
    _add_button_locator = (By.CSS_SELECTOR, "#form_buttons img[title='Add']")
    _cancel_button_locator = (By.CSS_SELECTOR, "#form_buttons img[title='Cancel']")

    @property
    def add_button(self):
        return self.selenium.find_element(*self._add_button_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_button_locator)

    def cancel(self):
        """ Clicks on Cancel button and returns back to the PolicyView

        @return: PolicyView
        """
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def add(self):
        """ Clicks on Add button and returns back to the PolicyConditionView

        @return: PolicyView
        """
        self.cancel_button.click()
        self._wait_for_results_refresh()
        assert "was added" in self.flash.message, self.flash.message
        return PolicyConditionView(self.testsetup)


class EditConditionForPolicy(BaseConditionForPolicy):
    """ Page representing an editation of an existing Condition

    Inherits and adds three buttons.

    """
    _save_locator = (By.CSS_SELECTOR, "#form_buttons img[title='Save Changes']")
    _cancel_locator = (By.CSS_SELECTOR, "#form_buttons img[title='Cancel']")
    _reset_locator = (By.CSS_SELECTOR, "#form_buttons img[title='Reset Changes']")

    @property
    def save_button(self):
        return self.selenium.find_element(*self._save_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_locator)

    @property
    def reset_button(self):
        return self.selenium.find_element(*self._reset_locator)

    def save(self):
        """ Save changes.

        @return: PolicyConditionView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=10)
        self.save_button.click()
        self._wait_for_results_refresh()
        return PolicyConditionView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyConditionView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyConditionView(self.testsetup)

    def reset(self):
        """ Reset changes.

        Stays on the page.
        @return: True if the flash message shows correct message.
        @rtype: bool
        """
        self._wait_for_visible_element(*self._reset_locator, visible_timeout=10)
        self.reset_button.click()
        self._wait_for_results_refresh()
        return "All changes have been reset" in self.flash.message


class CopyConditionForPolicy(NewConditionForPolicy):
    """ Copy policy screen is exactly the same but it returns to the Condition view
    rather than the Policy view. Therefore this inheritance

    """
    def cancel(self):
        """ Clicks on Cancel button and returns back to the PolicyConditionView

        @return: PolicyConditionView
        """
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyConditionView(self.testsetup)


class PolicyConditionView(Policies, RefreshMixin):
    _expression_locator = (By.XPATH, "//*[@id=\"condition_info_div\"]/fieldset[2]")
    _scope_locator = (By.XPATH, "//*[@id=\"condition_info_div\"]/fieldset[1]")
    _notes_textarea_locator = (By.CSS_SELECTOR, "textarea#notes")

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _configuration_remove_cond_locator = (By.CSS_SELECTOR,
                                         "tr[title*='Remove this Condition from Policy']")
    _configuration_edit_cond_locator = (By.CSS_SELECTOR,
                                        "tr[title='Edit this Condition']")
    _configuration_copy_cond_locator = (By.CSS_SELECTOR,
                                        "tr[title*='Copy this Condition to a new Condition']")

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_remove_cond_button(self):
        return self.selenium.find_element(*self._configuration_remove_cond_locator)

    @property
    def configuration_edit_cond_button(self):
        return self.selenium.find_element(*self._configuration_edit_cond_locator)

    @property
    def configuration_copy_cond_button(self):
        return self.selenium.find_element(*self._configuration_copy_cond_locator)

    @property
    def expression(self):
        return self.selenium.find_element(*self._expression_locator).text\
                                                                    .strip()\
                                                                    .split(":", 1)[-1]\
                                                                    .lstrip()

    @property
    def scope(self):
        return self.selenium.find_element(*self._scope_locator).text\
                                                               .strip()\
                                                               .split(":", 1)[-1]\
                                                               .lstrip()

    @property
    def notes_textarea(self):
        return self.selenium.find_element(*self._notes_textarea_locator)

    @property
    def notes(self):
        """ Returns contents of the notes textarea

        """
        if self.is_element_visible(*self._notes_textarea_locator):
            return self.notes_textarea.text.strip()
        else:
            return None

    @notes.setter
    def notes(self, value):
        """ Sets the contents of the notes textarea

        """
        self.notes_textarea.clear()
        self.notes_textarea.send_keys(value)

    def remove(self, cancel=False):
        """ Remove this condition

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_remove_cond_button)\
            .perform()
        self.handle_popup(cancel)
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def edit(self):
        """ Edit this condition

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_edit_cond_button)\
            .perform()
        self._wait_for_results_refresh()
        return EditConditionForPolicy(self.testsetup)

    def copy(self):
        """ Copy this condition to a new one under same policy

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_copy_cond_button)\
            .perform()
        self._wait_for_results_refresh()
        return CopyConditionForPolicy(self.testsetup)


class PolicyConditionAssignments(Policies):
    """ This class models the Condition assignment editor

    """
    _save_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    # Boxes
    _available_locator = (By.CSS_SELECTOR, "span#choices_chosen_div > select#choices_chosen")
    _used_locator = (By.CSS_SELECTOR, "span#members_chosen_div > select#members_chosen")

    # Manipulation buttons
    _use_condition_button = (By.CSS_SELECTOR,
            "a[title='Move selected Conditions into this Policy'] > img")
    _unuse_condition_button = (By.CSS_SELECTOR,
            "a[title='Remove selected Conditions from this Policy'] > img")
    _unuse_all_conditions_button = (By.CSS_SELECTOR,
            "a[title='Remove all Conditions from this Policy'] > img")

    @property
    def save_button(self):
        return self.selenium.find_element(*self._save_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_locator)

    @property
    def reset_button(self):
        return self.selenium.find_element(*self._reset_locator)

    @property
    def available_box(self):
        return self.selenium.find_element(*self._available_locator)

    @property
    def used_box(self):
        return self.selenium.find_element(*self._used_locator)

    @property
    def use_button(self):
        return self.selenium.find_element(*self._use_condition_button)

    @property
    def unuse_button(self):
        return self.selenium.find_element(*self._unuse_condition_button)

    @property
    def unuse_all_button(self):
        return self.selenium.find_element(*self._unuse_all_condition_button)

    @property
    def available_choices(self):
        """ Returns a list of all available conditions

        """
        return [e.text.strip() for e in self.available_box.find_elements_by_css_selector("option")]

    @property
    def used_choices(self):
        """ Returns a list of all used conditions

        """
        return [e.text.strip() for e in self.used_box.find_elements_by_css_selector("option")]

    @property
    def is_always_true(self):
        """ Returns a bool whether this conditional always evaluates as true

        """
        return len(self.used_choices) == 0

    def select_from_available(self, name):
        self.select_dropdown(name, *self._available_locator)

    def select_from_used(self, name):
        self.select_dropdown(name, *self._used_locator)

    def use_selected_condition(self):
        self.use_button.click()
        self._wait_for_results_refresh()
        return "No Conditions were selected to move right" not in self.flash.message

    def unuse_selected_condition(self):
        self.unuse_button.click()
        self._wait_for_results_refresh()
        return "No Conditions were selected to move left" not in self.flash.message

    def unuse_all_conditions(self):
        self.unuse_all_button.click()
        self._wait_for_results_refresh()
        return "No Conditions were selected to move left" not in self.flash.message

    def use_condition(self, name):
        self.select_from_available(name)
        return self.use_selected_condition()

    def unuse_condition(self, name):
        self.select_from_used(name)
        return self.unuse_selected_condition()

    def save(self):
        """ Save changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=10)
        self.save_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def reset(self):
        """ Reset changes.

        Stays on the page.
        @return: True if the flash message shows correct message.
        @rtype: bool
        """
        self._wait_for_visible_element(*self._reset_locator, visible_timeout=10)
        self.reset_button.click()
        self._wait_for_results_refresh()
        return "All changes have been reset" in self.flash.message


class PolicyEventAssignments(Policies):
    """ This class models the Event assignment editor

    """
    _save_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    @property
    def save_button(self):
        return self.selenium.find_element(*self._save_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_locator)

    @property
    def reset_button(self):
        return self.selenium.find_element(*self._reset_locator)

    def save(self):
        """ Save changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=10)
        self.save_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)

    def reset(self):
        """ Reset changes.

        Stays on the page.
        @return: True if the flash message shows correct message.
        @rtype: bool
        """
        self._wait_for_visible_element(*self._reset_locator, visible_timeout=10)
        self.reset_button.click()
        self._wait_for_results_refresh()
        return "All changes have been reset" in self.flash.message

    def search_by_name(self, name):
        checkbox_divs = self.selenium.find_elements_by_css_selector("div:contains('%s')" % name)
        for checkbox_div in checkbox_divs:
            if checkbox_div.text.strip() == name:
                return checkbox_div.find_element_by_css_selector("input[type='checkbox']")
        raise Exception("Event %s was not found!" % name)

    def set(self, name, check):
        """ Set checkbox with appropriate value

        """
        checkbox = self.search_by_name(name)
        if (not check and not checkbox.is_selected()) or (check and checkbox.is_selected()):
            return
        checkbox.click()

    def mass_set(self, dictionary):
        """ To make life easier, you can pass a dictionary to set everything in one step

        """
        for key, value in dictionary.iteritems():
            self.set(key, value)
        return self


class PolicyEventView(Policies, TaskbarMixin, RefreshMixin):
    _event_group_locator = (By.XPATH,
        "//*[@id='event_info_div']/fieldset[1]/table/tbody/tr[1]/td[2]")
    _policy_attached_locator = (By.XPATH,
        "//*[@id='event_info_div']/fieldset[1]/table/tbody/tr[2]/td[2]")

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _configuration_edit_actions_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title='Edit Actions for this Policy Event']")

    _table_actions_alltrue = (By.XPATH, "//*[@id='event_info_div']/fieldset[2]/table")
    _table_actions_anyfalse = (By.XPATH, "//*[@id='event_info_div']/fieldset[3]/table")

    @property
    def event_group(self):
        return self.selenium.find_element(*self._event_group_locator).text.strip()

    @property
    def policy_attached(self):
        return self.selenium.find_element(*self._policy_attached_locator).text.strip()

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_edit_actions(self):
        return self.selenium.find_element(*self._configuration_edit_actions_locator)

    @property
    def alltrue_actions_table(self):
        return self.selenium.find_element(*self._table_actions_alltrue)

    @property
    def anyfalse_actions_table(self):
        return self.selenium.find_element(*self._table_actions_anyfalse)

    def go_to_attached_policy(self):
        """ Reads name of the policy, then it searches for it in the accordion tree.

        """
        return self.select_policy(self.policy_attached)

    def edit_actions(self):
        """ Fire up the action edit page.

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_edit_actions)\
            .perform()
        self._wait_for_results_refresh()
        return PolicyEventActionsEdit(self.testsetup)

    @property
    def any_alltrue_action(self):
        """ This looks whether the table containing alltrue conditions is present

        """
        return self.is_element_visible(*self._table_actions_alltrue)

    @property
    def any_anyfalse_action(self):
        """ This looks whether the table containing anyfalse conditions is present

        """
        return self.is_element_visible(*self._table_actions_anyfalse)

    @property
    def alltrue_actions(self):
        """ List all alltrue actions.

        """
        if not self.any_alltrue_action:
            return []
        return self.alltrue_actions_table.find_elements_by_css_selector("tbody > tr")

    @property
    def anyfalse_actions(self):
        """ List all anyfalse actions.

        """
        if not self.any_anyfalse_action:
            return []
        return self.anyfalse_actions_table.find_elements_by_css_selector("tbody > tr")

    def get_action_description(self, action_element):
        """ Extracts table cells from the element row and names then in the dict()

        """
        return dict(zip(["img", "desc", "syn", "type"],
                        action_element.find_elements_by_css_selector("td")
                        ))


class PolicyEventActionsEdit(Policies):
    """ Assigning actions to policy events.

    For all functions and properties defined here:
    - if it contains "true" or "false" in the name, then it works with either top
      or bottom box on the page

    """
    _save_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    _event_group_locator = (By.XPATH,
        "//*[@id='event_info_div']/fieldset[1]/table/tbody/tr[1]/td[2]")
    _policy_attached_locator = (By.XPATH,
        "//*[@id='event_info_div']/fieldset[1]/table/tbody/tr[2]/td[2]")

    # Boxes
    _choices_chosen_true_locator = (By.CSS_SELECTOR, "select#choices_chosen_true")
    _members_chosen_true_locator = (By.CSS_SELECTOR, "select#members_chosen_true")
    _choices_chosen_false_locator = (By.CSS_SELECTOR, "select#choices_chosen_false")
    _members_chosen_false_locator = (By.CSS_SELECTOR, "select#members_chosen_false")

    # Buttons
    # Top section
    _choose_choice_true_locator = (By.CSS_SELECTOR,
        "a[data-submit='choices_chosen_true_div']"
        "[title='Move selected Actions into this Event'] > img")
    _remove_choice_true_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_true_div']"
        "[title='Remove selected Actions from this Event'] > img")
    _remove_all_true_locator = (By.CSS_SELECTOR, "a[href*='true_allleft'] > img")

    _move_member_up_true_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_true_div']"
        "[title='Move selected Action up'] > img")
    _move_member_down_true_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_true_div']"
        "[title='Move selected Action down'] > img")
    _set_member_sync_true_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_true_div']"
        "[title='Set selected Actions to Synchronous'] > img")
    _set_member_async_true_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_true_div']"
        "[title='Set selected Actions to Asynchronous'] > img")

    # Bottom section
    _choose_choice_false_locator = (By.CSS_SELECTOR,
        "a[data-submit='choices_chosen_false_div']"
        "[title='Move selected Actions into this Event'] > img")
    _remove_choice_false_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_false_div']"
        "[title='Remove selected Actions from this Event'] > img")
    _remove_all_false_locator = (By.CSS_SELECTOR, "a[href*='false_allleft'] > img")

    _move_member_up_false_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_false_div']"
        "[title='Move selected Action up'] > img")
    _move_member_down_false_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_false_div']"
        "[title='Move selected Action down'] > img")
    _set_member_sync_false_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_false_div']"
        "[title='Set selected Actions to Synchronous'] > img")
    _set_member_async_false_locator = (By.CSS_SELECTOR,
        "a[data-submit='members_chosen_false_div']"
        "[title='Set selected Actions to Asynchronous'] > img")

    # Misc
    _regexp_members = re.compile(r"^\((?P<type>[AS])\) (?P<name>.*?)$")

    # Main buttons
    @property
    def save_button(self):
        return self.selenium.find_element(*self._save_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_locator)

    @property
    def reset_button(self):
        return self.selenium.find_element(*self._reset_locator)

    # Boxes
    @property
    def true_available_actions_box(self):
        return self.selenium.find_element(*self._choices_chosen_true_locator)

    @property
    def true_selected_actions_box(self):
        return self.selenium.find_element(*self._members_chosen_true_locator)

    @property
    def false_available_actions_box(self):
        return self.selenium.find_element(*self._choices_chosen_false_locator)

    @property
    def false_selected_actions_box(self):
        return self.selenium.find_element(*self._members_chosen_false_locator)

    # TRUE middle buttons
    @property
    def true_move_right_button(self):
        return self.selenium.find_element(*self._choose_choice_true_locator)

    @property
    def true_move_left_button(self):
        return self.selenium.find_element(*self._remove_choice_true_locator)

    @property
    def true_remove_all_button(self):
        return self.selenium.find_element(*self._remove_all_true_locator)

    # TRUE right buttons
    @property
    def true_move_up_button(self):
        return self.selenium.find_element(*self._move_member_up_true_locator)

    @property
    def true_move_down_button(self):
        return self.selenium.find_element(*self._move_member_down_true_locator)

    @property
    def true_set_sync_button(self):
        return self.selenium.find_element(*self._set_member_sync_true_locator)

    @property
    def true_set_async_button(self):
        return self.selenium.find_element(*self._set_member_async_true_locator)

    # FALSE middle buttons
    @property
    def false_move_right_button(self):
        return self.selenium.find_element(*self._choose_choice_false_locator)

    @property
    def false_move_left_button(self):
        return self.selenium.find_element(*self._remove_choice_false_locator)

    @property
    def false_remove_all_button(self):
        return self.selenium.find_element(*self._remove_all_false_locator)

    # FALSE right buttons
    @property
    def false_move_up_button(self):
        return self.selenium.find_element(*self._move_member_up_false_locator)

    @property
    def false_move_down_button(self):
        return self.selenium.find_element(*self._move_member_down_false_locator)

    @property
    def false_set_sync_button(self):
        return self.selenium.find_element(*self._set_member_sync_false_locator)

    @property
    def false_set_async_button(self):
        return self.selenium.find_element(*self._set_member_async_false_locator)

    # Main buttons actions
    def save(self):
        """ Save changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=10)
        self.save_button.click()
        self._wait_for_results_refresh()
        return PolicyEventView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyEventView(self.testsetup)

    def reset(self):
        """ Reset changes.

        Stays on the page.
        @return: True if the flash message shows correct message.
        @rtype: bool
        """
        self._wait_for_visible_element(*self._reset_locator, visible_timeout=10)
        self.reset_button.click()
        self._wait_for_results_refresh()
        return "All changes have been reset" in self.flash.message

    def _get_available_actions(self, box):
        """ DRY method for gathering the actions from available box

        """
        return [(e.text.strip(), e.get_attribute("value"))
                for e
                in box.find_elements_by_css_selector("option")]

    @property
    def available_true_actions(self):
        """ Get list of all available actions in the top box

        """
        return self._get_available_actions(self.true_available_actions_box)

    @property
    def available_false_actions(self):
        """ Get list of all available actions in the bottom box

        """
        return self._get_available_actions(self.false_available_actions_box)

    def _get_selected_actions(self, box):
        """ DRY method for gathering the actions

        1) bool whether is the action synchronous
        2) Its displayed name
        3) Its value from <option ...> for better search.

        @param box: Element to look in
        @return: [(sync?, "name1", "value"), (sync?, "name2", "value"), ...] -> sync? = bool
        """
        def _tuplify(e):
            d = self._regexp_members.match(e.text.strip()).groupdict()
            return d["type"].upper() == "S", d["name"], e.get_attribute("value")
        return [_tuplify(e)
                for e
                in box.find_elements_by_css_selector("option")
                if self._regexp_members.match(e.text.strip())]

    @property
    def selected_true_actions(self):
        """ Get all TRUE selected actions and determine whether is it synchronous or not

        @return: [(sync?, "name1", "value"), (sync?, "name2", "value"), ...] -> sync? = bool
        """
        return self._get_selected_actions(self.true_selected_actions_box)

    @property
    def selected_false_actions(self):
        """ Get all FALSE selected actions and determine whether is it synchronous or not

        @return: [(sync?, "name1", "value"), (sync?, "name2", "value"), ...] -> sync? = bool
        """
        return self._get_selected_actions(self.false_selected_actions_box)

    def select_available_action_true(self, name):
        """ Select an item in the top left box

        """
        self.select_dropdown(name, *self._choices_chosen_true_locator)

    def select_available_action_false(self, name):
        """ Select an item in the bottom eft box

        """
        self.select_dropdown(name, *self._choices_chosen_false_locator)

    def select_selected_action_true(self, name):
        """ If an action with name is found, then it is selected and informations are returned

        """
        for sync, action_name, value in self.selected_true_actions:
            if action_name == name:
                self.select_dropdown_by_value(value, *self._members_chosen_true_locator)
                return sync, action_name, value
        raise Exception("Action %s not found!" % name)

    def select_selected_action_false(self, name):
        """ If an action with name is found, then it is selected and informations are returned

        """
        for sync, action_name, value in self.selected_false_actions:
            if action_name == name:
                self.select_dropdown_by_value(value, *self._members_chosen_false_locator)
                return sync, action_name, value
        raise Exception("Action %s not found!" % name)

    def is_action_enabled_true(self, name):
        """ Look for the actions in top right box.
            If not found, return None
        """
        for sync, action_name, value in self.selected_true_actions:
            if action_name == name:
                return value
        return None

    def is_action_enabled_false(self, name):
        """ Look for the actions in bottom right box.
            If not found, return None
        """
        for sync, action_name, value in self.selected_false_actions:
            if action_name == name:
                return value
        return False

    def enable_action_true(self, name):
        value = self.is_action_enabled_true(name)
        if value is None:
            self.select_available_action_true(name)
            self.true_move_right_button.click()
            self._wait_for_results_refresh()
        return self

    def disable_action_true(self, name):
        value = self.is_action_enabled_true(name)
        if value:
            self.select_dropdown_by_value(value, *self._members_chosen_true_locator)
            self.true_move_left_button.click()
            self._wait_for_results_refresh()
        return self

    def enable_action_false(self, name):
        value = self.is_action_enabled_false(name)
        if value is None:
            self.select_available_action_false(name)
            self.false_move_right_button.click()
            self._wait_for_results_refresh()
        return self

    def disable_action_false(self, name):
        value = self.is_action_enabled_false(name)
        if value:
            self.select_dropdown_by_value(value, *self._members_chosen_false_locator)
            self.false_move_left_button.click()
            self._wait_for_results_refresh()
        return self

    # Methods for moving the actions up and down
    def move_action_up_true(self, name):
        self.select_selected_action_true(name)
        self.true_move_up_button.click()
        self._wait_for_results_refresh()
        return self

    def move_action_up_false(self, name):
        self.select_selected_action_false(name)
        self.false_move_up_button.click()
        self._wait_for_results_refresh()
        return self

    def move_action_down_true(self, name):
        self.select_selected_action_true(name)
        self.true_move_down_button.click()
        self._wait_for_results_refresh()
        return self

    def move_action_down_false(self, name):
        self.select_selected_action_false(name)
        self.false_move_down_button.click()
        self._wait_for_results_refresh()
        return self

    def set_action_sync_true(self, name, synchronous):
        """ Set state of an action in TRUE section. Sync/Async

        """
        self.clear_selected_selection_true()
        sync, name, value = self.select_selected_action_true(name)
        if synchronous and not sync:
            self.true_set_sync_button.click()
            self._wait_for_results_refresh()
            return self
        if not synchronous and sync:
            self.true_set_async_button.click()
            self._wait_for_results_refresh()
            return self

    def set_action_sync_false(self, name, synchronous):
        """ Set state of an action in FALSE section. Sync/Async

        """
        self.clear_selected_selection_false()
        sync, name, value = self.select_selected_action_false(name)
        if synchronous and not sync:
            self.false_set_sync_button.click()
            self._wait_for_results_refresh()
            return self
        if not synchronous and sync:
            self.false_set_async_button.click()
            self._wait_for_results_refresh()
            return self

    def unselect_all_actions_true(self):
        for sync, name, value in self.selected_true_actions:
            self.disable_action_true(name)
        assert len(self.selected_true_actions) == 0

    def unselect_all_actions_false(self):
        for sync, name, value in self.selected_false_actions:
            self.disable_action_false(name)
        assert len(self.selected_false_actions) == 0

    # Methods for clearing selection
    def clear_available_selection_true(self):
        """ Clear selection for top left box

        """
        from selenium.webdriver.support.ui import Select
        Select(self.true_available_actions_box).deselect_all()

    def clear_selected_selection_true(self):
        """ Clear selection for top right box

        """
        from selenium.webdriver.support.ui import Select
        Select(self.true_selected_actions_box).deselect_all()

    def clear_available_selection_false(self):
        """ Clear selection for bottom left box

        """
        from selenium.webdriver.support.ui import Select
        Select(self.false_available_actions_box).deselect_all()

    def clear_selected_selection_false(self):
        """ Clear selection for bottom right box

        """
        from selenium.webdriver.support.ui import Select
        Select(self.false_selected_actions_box).deselect_all()
