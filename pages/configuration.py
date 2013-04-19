'''
Created on Mar 5, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.configuration_subpages.access_control import AccessControl
from pages.configuration_subpages.settings import Settings
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class Configuration(Base):
    @property
    def submenus(self):
        return {"configuration" : lambda: Configuration.Configuration,
                "mysettings"    : lambda: Configuration.MySettings,
                "tasks"         : lambda: Configuration.Tasks,
                "smartproxies"  : lambda: Configuration.SmartProxies,
                "about"         : lambda: Configuration.About
                }
        
    def __init__(self,setup):
        Base.__init__(self, setup)
        # TODO: Add more initialization here
    
    class Configuration(Base):
        _page_title = "CloudForms Management Engine: Configuration"

        @property
        def tabbutton_region(self):
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = (By.CSS_SELECTOR, "div#ops_tabs > ul > li"))

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            return Accordion(self.testsetup)

        def click_on_access_control(self):
            self.accordion.accordion_by_name('Access Control').click()
            self._wait_for_results_refresh()
            return AccessControl(self.testsetup)

        def click_on_settings(self):
            self.accordion.accordion_by_name('Settings').click()
            self._wait_for_results_refresh()
            return Settings(self.testsetup)

    class MySettings(Base):
        _page_title = "CloudForms Management Engine: Configuration"

        @property
        def tabbutton_region(self):
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = None)

    class Tasks(Base):
        _page_title = "CloudForms Management Engine: My Tasks"

        @property
        def tabbutton_region(self):
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = None)

    class SmartProxies(Base):
        _page_title = "CloudForms Management Engine: SmartProxies"

    class About(Base):
        _page_title = "CloudForms Management Engine: About"
