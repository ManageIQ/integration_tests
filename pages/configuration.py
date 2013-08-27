'''
Created on Mar 5, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.configuration_subpages.access_control import AccessControl
from pages.configuration_subpages.settings import Settings
from pages.configuration_subpages.tasks_tabs import Tasks
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains


class Configuration(Base):
    @property
    def submenus(self):
        return {"ops"        : Configuration.Configuration,
                "ui"         : Configuration.MySettings,
                "my_tasks"   : Tasks.MyVmAnalysisTasks,
                "miq_proxy"  : Configuration.SmartProxies,
                "about"      : Configuration.About
                }

    class Configuration(Base):
        _page_title = "CloudForms Management Engine: Configuration"
        _checkbox_automation_engine = (By.ID, "server_roles_automate")
        _save_button = (By.CSS_SELECTOR, \
                      "div#buttons_on > ul#form_buttons > li > \
                      img[alt='Save Changes']")

        @property
        def tabbutton_region(self):
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = \
                    (By.CSS_SELECTOR, "div#ops_tabs > ul > li"))

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
            return Accordion(self.testsetup, LegacyTreeAccordionItem)

        @property
        def automation_engine_checkbox(self):
            return self.get_element(*self._checkbox_automation_engine)

        @property
        def save_button(self):
            return self.get_element(*self._save_button)

        def click_on_access_control(self):
            self.accordion.accordion_by_name('Access Control').click()
            self._wait_for_results_refresh()
            return AccessControl(self.testsetup)

        def click_on_settings(self):
            self.accordion.accordion_by_name('Settings').click()
            self._wait_for_results_refresh()
            return Settings(self.testsetup)

        def enable_automation_engine(self):
            '''Enables Automation Engine'''
            if not automation_engine_checkbox.is_selected():
                automation_engine_checkbox.click()
                self._wait_for_visible_element(*self._save_button)
                save_button.click()
            self._wait_for_results_refresh()
            return Settings(self.testsetup)

        def click_on_redhat_updates(self):
            from pages.configuration_subpages.settings_subpages.\
                    region_subpages.redhat_updates import RedhatUpdates
            self.accordion.current_content.click()
            self._wait_for_results_refresh()
            self.tabbutton_region.tabbutton_by_name("Red Hat Updates").click()
            self._wait_for_results_refresh()
            return RedhatUpdates(self.testsetup)

    class MySettings(Base):
        _page_title = "CloudForms Management Engine: Configuration"

        @property
        def tabbutton_region(self):
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = None)

    class SmartProxies(Base):
        _page_title = "CloudForms Management Engine: SmartProxies"

    class About(Base):
        _page_title = "CloudForms Management Engine: About"
