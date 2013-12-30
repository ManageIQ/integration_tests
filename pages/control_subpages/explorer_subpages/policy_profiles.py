# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
from pages.control_subpages.explorer import Explorer
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.expression_editor_mixin import ExpressionEditorMixin


class PolicyProfiles(Explorer):
    """ Control / Explorer / Policy Profiles

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

    def _new_policy_profile(self, where):
        """ DRY method that takes the location in the tree and goes there.

        It then clicks on a Configuration/Add new (whatever continues) to open the page

        @return: NewPolicyProfile
        """
        self.accordion.current_content.get_node(where).click()
        self._wait_for_results_refresh()
        ActionChains(self.selenium)\
            .click(self.configuration_button)\
            .click(self.configuration_add_new_button)\
            .perform()
        self._wait_for_results_refresh()
        return NewPolicyProfile(self.testsetup)


class NewPolicyProfile(EditPolicyProfile):
    """ This is the edit page invoked when creating a new policy profile.

    Inherits EditPolicyProfile and adds Add/Cancel Buttons
    """
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

        @return: PolicyProfileView
        """
        self._wait_for_visible_element(*self._add_locator, visible_timeout=10)
        self.add_button.click()
        self._wait_for_results_refresh()
        result = PolicyProfileView(self.testsetup)
        if not result.is_element_present(*result._configuration_edit_basic_locator):
            # Workaround for a glitch that occurs in not-the-last version
            # DISCARDS FLASH MESSAGES!!
            result.reload()
            import time
            time.sleep(1)

        return result

    def cancel(self):
        """ Cancel changes.

        @return: PolicyProfileView
        """
        self._wait_for_visible_element(*self._cancel_locator, visible_timeout=5)
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return PolicyProfiles(self.testsetup)


class EditPolicyProfile(PolicyProfiles, ExpressionEditorMixin):
    """
    Basic Edit Policy Profile Actions and Components
    """
    _description_input_locator = (By.CSS_SELECTOR, "input#description")

    # Boxes
    _available_locator = (By.CSS_SELECTOR, "span#choices_chosen_div > select#choices_chosen")
    _used_locator = (By.CSS_SELECTOR, "span#members_chosen_div > select#members_chosen")

    # Manipulation buttons
    _use_policy_button = (
        By.CSS_SELECTOR,
        "a[title='Move selected Policies into this Profile'] > img")
    _unuse_policy_button = (
        By.CSS_SELECTOR,
        "a[title='Remove selected Policies from this Profile'] > img")
    _unuse_all_policies_button = (
        By.CSS_SELECTOR,
        "a[title='Remove all Policies from this Profile'] > img")

    @property
    def description_input(self):
        return self.selenium.find_element(*self._description_input_locator)

    @property
    def available_box(self):
        return self.selenium.find_element(*self._available_locator)

    @property
    def used_box(self):
        return self.selenium.find_element(*self._used_locator)

    @property
    def use_button(self):
        return self.selenium.find_element(*self._use_policy_button)

    @property
    def unuse_button(self):
        return self.selenium.find_element(*self._unuse_policy_button)

    @property
    def unuse_all_button(self):
        return self.selenium.find_element(*self._unuse_all_policies_button)

    @property
    def selected_true_policies(self):
        """ Get all TRUE selected policies and determine whether is it synchronous or not

        @return: [(sync?, "name1", "value"), (sync?, "name2", "value"), ...] -> sync? = bool
        """
        return self._get_selected_policies(self.used_box)

    def select_available_policy_true(self, name):
        """ Select an item in the top left box

        """
        self.select_dropdown(name, *self._available_locator)
        return self

    def _get_selected_policies(self, box):
        """ DRY method for gathering the policies

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

    def is_policy_enabled_true(self, name):
        """ Look for the policies in right box.

        @return: If not found, return None. Otherwise it returns the value to be able to select it.
        """
        for sync, action_name, value in self.selected_true_policies:
            if action_name == name:
                return value
        return None

    def enable_policy_true(self, name):
        """ Select an action from TRUE available box and move it to the right

        """
        value = self.is_policy_enabled_true(name)
        if value is None:
            self.select_available_policy_true(name)
            self.use_button.click()
            self._wait_for_results_refresh()
        return self


class PolicyProfileView(PolicyProfiles):
    pass
