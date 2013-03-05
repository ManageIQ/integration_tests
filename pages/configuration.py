'''
Created on Mar 5, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By

class Configuration(Base):
    @property
    def submenus(self):
        return {"configuration" : lambda: Configuration.MySettings,
                }
        
    def __init__(self,setup):
        Base.__init__(self, setup)
        # TODO: Add more initialization here
    
    class MySettings(Base):
        _page_title = "CloudForms Management Engine: Configuration"
        
        def __init__(self,setup):
            Base.__init__(self, setup)
    