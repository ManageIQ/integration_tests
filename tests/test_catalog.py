#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from pages.page import Page
from selenium.webdriver.common.by import By

@pytest.mark.nondestructive 
class TestCatalogs:
    
    def test_create_service_dialog(self, mozwebqa, home_page_logged_in):
        aut_pg = home_page_logged_in.header.site_navigation_menu("Automate").sub_navigation_menu("Customization").click()
        new_dialog_pg = aut_pg.click_on_service_dialog_accordion().add_new_service_dialog()
        new_dialog_pg.create_service_dialog('auto_catalog_dialog','description')
        Assert.true(new_dialog_pg.flash.message.startswith('Dialog "auto_catalog_dialog" was added')) 
    

     
   