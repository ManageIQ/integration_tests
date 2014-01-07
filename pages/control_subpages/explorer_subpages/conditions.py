from pages.control_subpages.explorer import Explorer
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.control_subpages.explorer_subpages.shared import ConditionEditor
from pages.regions.taskbar.reload import ReloadMixin


class Conditions(Explorer):
    """ Control / Explorer / Conditions

    """

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _configuration_add_cond_locator = (By.CSS_SELECTOR,
                                       "tr[title*='Add a New']")

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_add_cond_button(self):
        return self.selenium.find_element(*self._configuration_add_cond_locator)

    def _add_new(self):
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_add_cond_button)\
            .perform()
        self._wait_for_results_refresh()
        return NewCondition(self.testsetup)

    def add_new_host_condition(self):
        self.accordion.current_content.get_node("Host Conditions").click()
        return self._add_new()

    def add_new_vm_condition(self):
        self.accordion.current_content.get_node("VM Conditions").click()
        return self._add_new()

    @property
    def all_host_conditions(self):
        """ Get all children of Host Conditons node

        """
        try:
            return self.accordion.current_content.get_nodes("Host Conditions")
        except AssertionError:
            return []

    @property
    def all_vm_conditions(self):
        """ Get all children of VM Conditons node

        """
        try:
            return self.accordion.current_content.get_nodes("VM Conditions")
        except AssertionError:
            return []

    def _select_condition(self, name, where=None):
        """ DRY method to go to specific condition

        @param name: Name of the condition
        @param where: Section where to look for it (Host Conditions, VM Conditions)
                      If None, will search it in both

        """
        location = "%s::%s" % (where, name)
        try:
            if where:
                self.accordion.current_content.get_node(location).click()
            else:
                self.accordion\
                    .current_content\
                    .find_node_by_name(name, img_src_contains="miq_condition")\
                    .click()
        except AttributeError:
            raise Exception("Could not find condition %s" % location)
        self._wait_for_results_refresh()
        return ConditionView(self.testsetup)

    def select_host_condition(self, name):
        """ Go to ConditionView with host condition

        """
        return self._select_condition(name, "Host Conditions")

    def delete_host_condition(self, name, cancel=False):
        """ Delete Host condition with specified name

        @return: Conditions
        """
        return self.select_host_condition(name).delete(cancel)

    def edit_host_condition(self, name):
        """ Open the edit window of a Host condition with specified name

        @return: EditCondition
        """
        return self.select_host_condition(name).edit()

    def copy_host_condition(self, name):
        """ Open the edit/copy window of a Host condition with specified name

        @return: CopyCondition
        """
        return self.select_host_condition(name).copy()

    def select_vm_condition(self, name):
        """ Go to ConditionView with vm condition

        """
        return self._select_condition(name, "VM Conditions")

    def delete_vm_condition(self, name, cancel=False):
        """ Delete VM condition with specified name

        @return: Conditions
        """
        return self.select_vm_condition(name).delete(cancel)

    def edit_vm_condition(self, name):
        """ Open the edit window of a VM condition with specified name

        @return: EditCondition
        """
        return self.select_vm_condition(name).edit()

    def copy_vm_condition(self, name):
        """ Open the edit/copy window of a VM condition with specified name

        @return: CopyCondition
        """
        return self.select_vm_condition(name).copy()

    def select_condition(self, name):
        """ Go to ConditionView with any condition

        """
        return self._select_condition(name)

    def delete_condition(self, name, cancel=False):
        """ Delete any condition with specified name

        @return: Conditions
        """
        return self.select_condition(name).delete(cancel)

    def edit_condition(self, name):
        """ Open the edit window of any condition with specified name

        @return: EditCondition
        """
        return self.select_condition(name).edit()

    def copy_condition(self, name):
        """ Open the edit/copy window of any condition with specified name

        @return: CopyCondition
        """
        return self.select_condition(name).copy()


class ConditionView(Conditions, ReloadMixin):
    """ General view on a condition's summary

    """
    _scope_locator = (By.XPATH, "//*[@id='condition_info_div']/fieldset[1]")
    _expression_locator = (By.XPATH, "//*[@id='condition_info_div']/fieldset[2]")

    _assigned_policies_table_locator = (By.XPATH, "//*[@id='condition_info_div']/fieldset[4]/table")

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _configuration_delete_cond_locator = (By.CSS_SELECTOR,
                                         "tr[title*='Delete this']")
    _configuration_edit_cond_locator = (By.CSS_SELECTOR,
                                        "tr[title='Edit this Condition']")
    _configuration_copy_cond_locator = (By.CSS_SELECTOR,
                                        "tr[title*='Copy this Condition to a new Condition']")

    _notes_textarea_locator = (By.CSS_SELECTOR, "textarea#notes")

    @property
    def notes_textarea(self):
        return self.selenium.find_element(*self._notes_textarea_locator)

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def configuration_delete_cond_button(self):
        return self.selenium.find_element(*self._configuration_delete_cond_locator)

    @property
    def configuration_edit_cond_button(self):
        return self.selenium.find_element(*self._configuration_edit_cond_locator)

    @property
    def configuration_copy_cond_button(self):
        return self.selenium.find_element(*self._configuration_copy_cond_locator)

    @property
    def scope(self):
        node = self.selenium.find_element(*self._scope_locator)
        return node.text.strip()

    @property
    def expression(self):
        node = self.selenium.find_element(*self._expression_locator)
        return node.text.strip()

    @property
    def assigned_policies_table(self):
        return self.selenium.find_element(*self._assigned_policies_table_locator)

    @property
    def has_policies(self):
        return len(self.list_assigned_policies) > 0

    @property
    def list_assigned_policies(self):
        """ Look for table with assigned policies and if present, return list of clickable elements

        """
        result = []
        if not self.is_element_visible(*self._assigned_policies_table_locator):
            return result
        for policy in self.assigned_policies_table.find_elements_by_css_selector("tbody > tr"):
            icon, description = policy.find_elements_by_css_selector("td")
            result.append(description)
        return result

    def go_to_policy(self, policy_name):
        """ Search policies and click on found one

        This cycles through all the table of policies and searches for the sought one.
        When found, it clicks on it and returns its view.

        @return: PolicyView
        @raise: Exception when not found
        """
        present = []
        for policy, scopes in self.list_assigned_policies:
            if policy.text.strip() == policy_name.strip():
                policy.click()
                self._wait_for_results_refresh()
                from pages.control_subpages.explorer_subpages.policies import PolicyView
                return PolicyView(self.testsetup)
            present.append(policy.text.strip())
        raise Exception("Policy with description %s was not found (%s present)" %
            (policy_name, ", ".join(present))
        )

    @property
    def notes(self):
        """ Returns contents of the notes textarea

        """
        return self.notes_textarea.text.strip()

    def delete(self, cancel=False):
        """ Remove this condition

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_delete_cond_button)\
            .perform()
        self.handle_popup(cancel)
        self._wait_for_results_refresh()
        return Conditions(self.testsetup)

    def edit(self):
        """ Edit this condition

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_edit_cond_button)\
            .perform()
        self._wait_for_results_refresh()
        return EditCondition(self.testsetup)

    def copy(self):
        """ Copy this condition to a new one under same policy

        """
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_copy_cond_button)\
            .perform()
        self._wait_for_results_refresh()
        return CopyCondition(self.testsetup)


class BaseConditionEdit(Conditions, ConditionEditor):
    """ General editing class, used for inheriting

    """
    # We must check that the notes textarea is editable - we are on the correct page
    _notes_textarea_locator = (By.CSS_SELECTOR, "textarea#notes:not([readonly='true'])")

    # Override the read-only notes
    @property
    def notes_textarea(self):
        self._wait_for_visible_element(*self._notes_textarea_locator, visible_timeout=5)
        return self.selenium.find_element(*self._notes_textarea_locator)

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


class NewCondition(BaseConditionEdit):
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
        return Conditions(self.testsetup)

    def add(self):
        """ Clicks on Add button and returns back to the PolicyConditionView

        @return: PolicyView
        """
        self.add_button.click()
        self._wait_for_results_refresh()
        assert "was added" in self.flash.message, self.flash.message
        return ConditionView(self.testsetup)


class EditCondition(BaseConditionEdit):
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
        return ConditionView(self.testsetup)

    def cancel(self):
        """ Cancel changes.

        @return: PolicyConditionView
        """
        self._wait_for_visible_element(*self._save_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return ConditionView(self.testsetup)

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


class CopyCondition(NewCondition):
    """ Copy condition screen is exactly the same but it returns to the Condition view
    rather than the Policy view. Therefore this inheritance

    """
    def cancel(self):
        """ Clicks on Cancel button and returns back to the ConditionView

        @return: ConditionView
        """
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return ConditionView(self.testsetup)

"""
@todo: Maybe use the classes from policies.py and inherit them, because the difference is small.
 """
