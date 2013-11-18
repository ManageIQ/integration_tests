# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
from pages.control_subpages.explorer import Explorer
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.taskbar.taskbar import TaskbarMixin
from pages.regions.expression_editor_mixin import ExpressionEditorMixin


class Policies(Explorer):
    """ Control / Explorer / Policies

    """

    def select_policy(self, policy):
        """ Selects policy by its name

        @return: PolicyView
        """
        node = self.accordion.current_content.find_node_by_name(policy,
                                                                img_src_contains="miq_policy_vm")
        try:
            node.click()
        except AttributeError:
            raise Exception("Policy '%s' not found!" % policy)
        self._wait_for_results_refresh()
        return PolicyView(self.testsetup)


class PolicyView(Policies, TaskbarMixin):
    """ This page represents the view on the policy with its details

    """
    _refresh_locator = (By.XPATH, "//*[@id='miq_alone']/img")
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

    @property
    def refresh_button(self):
        return self.selenium.find_element(*self._refresh_locator)

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_edit_basic_button(self):
        return self.selenium.find_element(*self._configuration_edit_basic_locator)

    @property
    def configuration_new_condition_button(self):
        return self.selenium.find_element(*self._configuration_new_condition_locator)

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

    def refresh(self):
        self.refresh_button.click()
        self._wait_for_results_refresh()
        return self

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
                return PolicyConditionView(self.testsetup)
            present.append(condition.text.strip())
        raise Exception("Condition with description %s was not found (%s present)" %
            (condition_name, ", ".join(present))
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


class BasicEditPolicy(Policies, ExpressionEditorMixin):
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

    _save_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

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
        """ Clicks on Add button and returns back to the PolicyView

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


class PolicyConditionView(Policies):
    _refresh_locator = (By.XPATH, "//*[@id='miq_alone']/img")
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
    def refresh_button(self):
        return self.selenium.find_element(*self._refresh_locator)

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

    def refresh(self):
        self.refresh_button.click()
        self._wait_for_results_refresh()
        return self
