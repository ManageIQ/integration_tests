'''
Created on Mar 5, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
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

