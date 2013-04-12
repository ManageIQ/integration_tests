from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class AccessControl(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _roles_button = (By.CSS_SELECTOR, "div[title='View Roles']")

    def click_on_roles(self):
        self.selenium.find_element(*self._roles_button).click()
        self._wait_for_results_refresh()
        return AccessControl.Roles(self.testsetup)

    class Roles(Base):
        _page_title = 'CloudForms Management Engine: Configuration'
        _add_role_button = (By.CSS_SELECTOR, "a[title='Add a new Role']")

        def click_on_add_new(self):
            self.selenium.find_element(*self._add_role_button).click()
            self._wait_for_results_refresh()
            return AccessControl.NewRole(self.testsetup)

        def click_on_role(self, role_name):
            selector = "td[title='%s']" % role_name
            self.selenium.find_element_by_css_selector(selector).click()
            self._wait_for_results_refresh()
            return AccessControl.ShowRole(self.testsetup)

    class NewRole(Base):
        _submit_role_button = (By.CSS_SELECTOR, "img[title='Add this Role']")
        _name_field = (By.CSS_SELECTOR, "input[name='name']")
        _access_restriction_field = (By.CSS_SELECTOR, "select[name='vm_restriction']")

        def fill_name(self, name):
            return self.selenium.find_element(*self._name_field).send_keys(name)

        def save(self):
            # when editing an existing role, wait until "save" button shows up
            # after ajax validation
            self._wait_for_visible_element(*self._submit_role_button)
            self.selenium.find_element(*self._submit_role_button).click()
            self._wait_for_results_refresh()
            return AccessControl.ShowRole(self.testsetup)

        def select_access_restriction(self, value):
            Select(self.selenium.find_element(*self._access_restriction_field)).select_by_value(value)

    class EditRole(NewRole):
        _name_field = (By.CSS_SELECTOR, "input[name='name']")
        _submit_role_button = (By.CSS_SELECTOR, "img[title='Save Changes']")

        def fill_name(self, name):
            field = self.selenium.find_element(*self._name_field)
            field.clear()
            field.send_keys(name)

    class ShowRole(Base):
        _edit_role_button = (By.CSS_SELECTOR, "a[title='Edit this Role']")
        _delete_role_button = (By.CSS_SELECTOR, "a[title='Delete this Role']")
        _role_name_label = (By.CSS_SELECTOR, ".style1 tr:nth-child(1) td:nth-child(2)")

        def click_on_edit(self):
            self.selenium.find_element(*self._edit_role_button).click()
            self._wait_for_results_refresh()
            return AccessControl.EditRole(self.testsetup)

        def click_on_delete(self):
            self.selenium.find_element(*self._delete_role_button).click()
            self.handle_popup()
            self._wait_for_results_refresh()
            return AccessControl.Roles(self.testsetup)

        @property
        def role_name(self):
            return self.selenium.find_element(*self._role_name_label).text.strip()
