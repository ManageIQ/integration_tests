from pages.control_subpages.explorer import Explorer
from selenium.webdriver.common.by import By


class Conditions(Explorer):
    """ Control / Explorer / Conditions

    """

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

    def _view_condition(self, name, where=None):
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

    def view_host_condition(self, name):
        """ Go to ConditionView with host condition

        """
        return self._view_condition(name, "Host Conditions")

    def view_vm_condition(self, name):
        """ Go to ConditionView with vm condition

        """
        return self._view_condition(name, "VM Conditions")

    def view_condition(self, name):
        """ Go to ConditionView with any condition

        """
        return self._view_condition(name)


class ConditionView(Conditions):
    """ General view on a condition's summary

    """
    _scope_locator = (By.XPATH, "//*[@id='condition_info_div']/fieldset[1]")
    _expression_locator = (By.XPATH, "//*[@id='condition_info_div']/fieldset[2]")

    _assigned_policies_table_locator = (By.XPATH, "//*[@id='condition_info_div']/fieldset[4]/table")

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
        if not self.is_element_visible(*self._assigned_policies_table_locator):
            return []
        result = []
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

"""
@todo: Maybe use the classes from policies.py and inherit them, because the difference is small.
"""
