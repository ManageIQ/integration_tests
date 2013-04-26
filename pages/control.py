# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time


class Control(Base):
    @property
    def submenus(self):
        return {"miq_policy": Control.Explorer,
                "miq_policy_export": Control.ImportExport
                }

    class Explorer(Base):
        _page_title = 'CloudForms Management Engine: Control'
        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)

        def click_on_events_accordion(self):
            self.accordion.accordion_by_name("Events").click()
            self._wait_for_results_refresh()
            return Control.Events(self.testsetup)

        def click_on_actions_accordion(self):
            self.accordion.accordion_by_name("Actions").click()
            self._wait_for_results_refresh()
            return Control.Actions(self.testsetup)

    class Events(Explorer):
        _events_table = (By.CSS_SELECTOR, "div#event_list_div fieldset table tbody")
        _event_row_locator = (By.XPATH, "tr")
        _event_items_locator = (By.XPATH, "td")

        @property
        def root(self):
            return self.selenium.find_element(*self._events_table).find_elements(*self._event_row_locator)

        @property
        def events(self):
            elements = [element.find_elements(*self._event_items_locator) for element in self.root]
            events = [(img, event_desc.text) for img, event_desc in elements]
            return events

        @property
        def events_list(self):
            return [event[1] for event in self.events]

        @property
        def print_events_list(self):
            # for generating default events list
            for event in self.events:
                print "'%s'," % event[1]

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
            return Control.NewAction(self.testsetup)

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
            return Control.Actions(self.testsetup)

    class ImportExport(Base):
        _page_title = 'CloudForms Management Engine: Control'
        _upload_button = (By.ID, "upload_atags")
        _commit_button = (By.CSS_SELECTOR, "a[title='Commit Import']")
        _policy_import_field = (By.ID, "upload_file")

        @property
        def upload(self):
            return self.selenium.find_element(*self._upload_button)
        
        @property
        def commit(self):
            return self.selenium.find_element(*self._commit_button)

        def click_on_upload(self):
            self.upload.click()
            self._wait_for_results_refresh()
            return Control.ImportExport(self.testsetup)

        def click_on_commit(self):
            self.commit.click()
            self._wait_for_results_refresh()
            return Control.ImportExport(self.testsetup)

        def import_policies(self, import_policy_file):
            self.selenium.find_element(*self._policy_import_field).send_keys(import_policy_file)
            return self.click_on_upload()
