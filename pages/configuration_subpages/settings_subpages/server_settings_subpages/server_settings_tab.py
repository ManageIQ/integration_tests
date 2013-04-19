from pages.base import Base
from selenium.webdriver.common.by import By

class ServerSettingsTab(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _server_roles_selector = (By.CSS_SELECTOR, ".col2 > dd > fieldset:nth-child(2) input[name*='server_roles']")
    _submit_button = (By.CSS_SELECTOR, "img[title='Save Changes']")

    @property
    def _server_role_elements(self):
        return self.selenium.find_elements(*self._server_roles_selector)

    @property
    def server_roles(self):
        return [ServerSettingsTab.ServerRole(el) for el in self._server_role_elements]

    def save(self):
        self._wait_for_visible_element(*self._submit_button)
        self.selenium.find_element(*self._submit_button).click()
        self._wait_for_results_refresh()
        return ServerSettingsTab(self.testsetup)

    def select_server_role(self, role_name):
        for role in self.server_roles:
            if role.name == role_name:
                role.select()

    def unselect_server_role(self, role_name):
        for role in self._server_role_elements:
            if role.name == role_name:
                role.unselect()

    def set_server_roles(self, roles):
        for role in self._server_role_elements:
            if role.name in roles:
                role.select()
            else:
                role.unselect()

    class ServerRole:
        def __init__(self, element):
            self.element = element

        def select(self):
            if not self.is_selected: self.element.click()

        def unselect(self):
            if self.is_selected: self.element.click()

        @property
        def name(self):
            return self.element.get_attribute('name')

        @property
        def is_selected(self):
            return self.element.is_selected()
