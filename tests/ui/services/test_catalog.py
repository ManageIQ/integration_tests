#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert
from pages.page import Page
from selenium.webdriver.common.by import By

@pytest.mark.nondestructive 
class TestCatalogs:
    
    service_dialog_name = "auto_catalog_dialog"
    service_dialog_desc = "service_desc"
    catalog_name = "auto_catalog"
    catalog_description = "cat_desc"
    catalog_item_name = "auto_cat_item"
    catalog_item_desc = "item_desc"
    catalog_bundle_name = "auto_bundle_name"
    catalog_bundle_desc = "bundle_desc"
    template = "linux_template"
    vm_name = "auto_test_vm"
    


    def test_create_service_dialog(self, mozwebqa, home_page_logged_in):
        aut_pg = home_page_logged_in.header.site_navigation_menu("Automate").sub_navigation_menu("Customization").click()
        new_dialog_pg = aut_pg.click_on_service_dialog_accordion().add_new_service_dialog()
        new_dialog_pg.create_service_dialog(self.service_dialog_name,self.service_dialog_desc)
        Assert.true(new_dialog_pg.flash.message.startswith('Dialog "%s" was added' % self.service_dialog_name)) 
    
    def test_create_catalog(self, mozwebqa, home_page_logged_in):
        cat_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Catalogs").click()
        Assert.true(cat_pg.is_the_current_page)
        new_cat_pg = cat_pg.click_on_catalogs_accordion().add_new_catalog()
        new_cat_pg.fill_name(self.catalog_name)
        new_cat_pg.fill_desc(self.catalog_description)
        show_cat_pg = new_cat_pg.save()
        Assert.true(show_cat_pg.flash.message.startswith('ServiceTemplateCatalog "%s" was saved' % self.catalog_name)) 
    
    def test_create_catalog_item(self, mozwebqa, home_page_logged_in):
        cat_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Catalogs").click()
        Assert.true(cat_pg.is_the_current_page)
        new_cat_item_pg = cat_pg.click_on_catalog_item_accordion().add_new_catalog_item()
        new_cat_item_pg.choose_catalog_item_type('VMware')
        new_cat_item_pg.fill_basic_info(self.catalog_item_name,self.catalog_item_desc,self.catalog_name,self.service_dialog_name,"2")
        req_pg = new_cat_item_pg.click_on_request_info_tab()
        req_pg.fill_catalog_tab(self.template,self.vm_name)
        envt_pg = req_pg.click_on_environment_tab()
        item_pg = envt_pg.fill_environment_tab("qeblade28.rhq.lab.eng.bos.redhat.com","datastore1")
        Assert.true(item_pg.flash.message.startswith('Service Catalog Item "%s" was added' % self.catalog_item_name)) 
        
    def test_create_catalog_bundle(self, mozwebqa, home_page_logged_in):
        bun_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Catalogs").click()
        Assert.true(bun_pg.is_the_current_page)
        new_bundle_pg = bun_pg.click_on_catalog_item_accordion().add_new_catalog_bundle()
        new_bundle_pg.fill_bundle_basic_info(self.catalog_bundle_name, self.catalog_bundle_desc,self.catalog_name,self.service_dialog_name, "2")
        res_pg = new_bundle_pg.click_on_resources_tab()
        res_pg.select_catalog_item(self.catalog_item_name)
        Assert.true(res_pg.flash.message.startswith('Catalog Bundle "%s" was added' % self.catalog_bundle_name))
        
    def test_service_catalog(self, mozwebqa, home_page_logged_in):
        sc_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Catalogs").click()
        Assert.true(sc_pg.is_the_current_page)
        table_pg = sc_pg.click_on_service_catalogs_accordion().click_on_catalog_in_service_tree(self.catalog_name)
        order_pg = table_pg.select_catalog_item(self.catalog_item_name)
        Assert.true(order_pg.flash.message.startswith('Order Request was Submitted')) 
       
     
   