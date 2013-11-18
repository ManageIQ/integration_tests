from selenium.webdriver.common.by import By
from pages.control_subpages.explorer import Explorer
from selenium.webdriver.common.action_chains import ActionChains
from pages.base import Base


class Actions(Explorer):
    _actions_table = (By.CSS_SELECTOR, "div#records_div table tbody")
    _action_row_locator = (By.XPATH, "tr")
    _action_items_locator = (By.XPATH, "td")

    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _add_action_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a new Action']")

    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def add_action_button(self):
        return self.selenium.find_element(*self._add_action_button_locator)

    def click_on_add_new(self):
        ActionChains(self.selenium).click(self.configuration_button).click(self.add_action_button).perform()
        self._wait_for_results_refresh()
        return self.NewAction(self.testsetup)

    @property
    def root(self):
        return self.selenium.find_element(*self._actions_table).find_elements(*self._action_row_locator)

    @property
    def actions(self):
        elements = [element.find_elements(*self._action_items_locator) for element in self.root]
        return [[img, a_desc.text, a_type.text] for img, a_desc, a_type in elements]

    @property
    def actions_list(self):
        elements = [element.find_elements(*self._action_items_locator) for element in self.root]
        return [(action[1], action[2]) for action in self.actions]

    @property
    def print_actions_list(self):
        # for generating default actions list
        for action in self.actions:
            print "('%s', '%s')," % (action[1], action[2])

    def actions_list(self):
        return [(action[1], action[2]) for action in self.actions]

    @property
    def print_actions_list(self):
        # for generating default actions list
        for action in self.actions:
            print "('%s', '%s')," % (action[1], action[2])

    class NewAction(Base):
        _description_field = (By.CSS_SELECTOR, "input#description")
        _type = (By.CSS_SELECTOR, "select#miq_action_type")
        _add_button = (By.CSS_SELECTOR, "img[title='Add']")

        # TODO: resolve wait after select dropdown issue and save valid action

        def add_invalid_action(self, description=None):
            self.selenium.find_element(*self._description_field).send_keys(description or "custom action")
            #self.select_dropdown(_a_type, *self._type)
            #self._wait_for_results_refresh()
            return self.click_on_add()

        def click_on_add(self):
            self.selenium.find_element(*self._add_button).click()
            self._wait_for_results_refresh()
            return Actions(self.testsetup)
