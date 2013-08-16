'''Created on July 25, 2013

@author: Shveta
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.services_subpages.provision import Provision
from pages.services_subpages.provision_subpages.provision_environment \
      import ProvisionEnvironment
from pages.services_subpages.provision_subpages.provision_catalog \
    import ProvisionCatalog
import time



class CatalogItems(Base):
    '''Catalog Item page'''
    _page_title = 'CloudForms Management Engine: Catalogs'
    _configuration_button_locator = (
        By.CSS_SELECTOR, 
        "div.dhx_toolbar_btn[title='Configuration']")
    _add_catalogitem_button_locator = (
        By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Add a New Catalog Item']")
    _add_catalogbundle_button_locator = (
        By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Add a New Catalog Bundle']")
    _del_catalog_item_locator = (
            By.CSS_SELECTOR, 
            "table.buttons_cont tr[title='Remove this Item from the VMDB']")
    _edit_catalog_bundle_locator = (
            By.CSS_SELECTOR, 
            "table.buttons_cont tr[title='Edit this Item']")
    
    @property
    def accordion(self):
        '''accordion'''
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
        return Accordion(self.testsetup, LegacyTreeAccordionItem)
     
    @property
    def configuration_button(self):
        '''Configuration btn'''
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def add_catalogitem_button(self):
        '''Add catalog item'''
        return self.selenium.find_element(*self._add_catalogitem_button_locator)
        
    def add_new_catalog_item(self):
        '''click on Configuration and then Add new catalog item btn'''
        ActionChains(self.selenium).click(
            self.configuration_button).click(
            self.add_catalogitem_button).perform()
        return CatalogItems.NewCatalogItem(self.testsetup)
    
    @property
    def add_catalogbundle_button(self):
        '''Add catalog bundle btn'''
        return self.selenium.find_element(
                *self._add_catalogbundle_button_locator)
        
    def add_new_catalog_bundle(self):
        '''Click on Configuration and then add new bundle btn'''
        ActionChains(self.selenium).click(
            self.configuration_button).click(
                self.add_catalogbundle_button).perform()
        return CatalogItems.NewCatalogBundle(self.testsetup)
    
    @property
    def del_catalog_item_btn(self):
        '''Delete catalog button'''
        return self.selenium.find_element(*self._del_catalog_item_locator)
    
    def delete_catalog_item(self):
        '''Delete catalog'''
        ActionChains(self.selenium).click(
            self.configuration_button).click(self.del_catalog_item_btn).perform()
        self.handle_popup()
        self._wait_for_results_refresh()
        return CatalogItems(self.testsetup)
    
    @property
    def edit_catalog_bundle_btn(self):
        '''Delete catalog button'''
        return self.selenium.find_element(*self._edit_catalog_bundle_locator)
    
    def edit_catalog_bundle(self):
        '''Delete catalog'''
        ActionChains(self.selenium).click(
            self.configuration_button).click(self.edit_catalog_bundle_btn).perform()
        self._wait_for_results_refresh()
        return CatalogItems.NewCatalogBundle(self.testsetup)
    
    def click_on_catalog_item(self, _catalog_item):
        '''Click on catalog to edit or delete'''
        self.accordion.current_content.find_node_by_name(_catalog_item).click()
        self._wait_for_results_refresh()
        return CatalogItems(self.testsetup)
    
    class NewCatalogItem(Provision):
        '''New Catalog Item page'''
        _catalog_item_type = (By.CSS_SELECTOR, "select#st_prov_type")
        _name_field = (By.CSS_SELECTOR, "input[name='name']")
        _desc_field = (By.CSS_SELECTOR, "input[name='description']")
        _display_checkbox = (By.CSS_SELECTOR, "input[name='display']")
        _select_catalog = (By.CSS_SELECTOR, "select#catalog_id")
        _select_dialog = (By.CSS_SELECTOR, "select#dialog_id")
        _cost_field = (By.CSS_SELECTOR, "input[name='provision_cost']")
         
        @property
        def tabbutton_region(self):
            '''tab buttons'''
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(
                self.testsetup,locator_override = (
                By.CSS_SELECTOR, "div#st_form_tabs > ul > li"))
         
        def click_on_request_info_tab(self):
            '''Click on Reuqest info tab'''
            self.tabbutton_region.tabbutton_by_name('Request Info').click()
            self._wait_for_results_refresh()
            return CatalogItems.NewCatalogItem(self.testsetup)
         
        def click_on_environment_tab(self):
            '''Click on environment tab'''
            Provision(self).tabbutton_region.tabbutton_by_name(
                    'Environment').click()
            self._wait_for_results_refresh()
            return CatalogItems.Environmenttab(self.testsetup)
         
        def choose_catalog_item_type(self, catalog_item_type):
            '''Choose catalog item type'''
            self.select_dropdown(catalog_item_type, *self._catalog_item_type)
            self._wait_for_results_refresh()
            return CatalogItems.NewCatalogItem(self.testsetup)
         
        def fill_basic_info(self, name, desc, catalog, dialog, cost):
            '''Fill basic info form'''
            self.selenium.find_element(*self._display_checkbox).click()
            time.sleep(2)
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._name_field).send_keys(name)
            self.selenium.find_element(*self._desc_field).send_keys(desc)
            self.select_dropdown(catalog, *self._select_catalog)
            self._wait_for_results_refresh()
            self.select_dropdown(dialog, *self._select_dialog)
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._cost_field).send_keys(cost)
            
        def fill_catalog_tab(self, template_name, _vm_name):
            '''Provisioning form - catalog tab'''
            catalog_item = None
            for item in ProvisionCatalog(self).catalog_list.items:
                if item.name == template_name:
                    catalog_item = item
                    print item.name
            catalog_item.click()
            self._wait_for_results_refresh()
            ProvisionCatalog(self).vm_name.send_keys(_vm_name)
            return CatalogItems.NewCatalogItem(self.testsetup)
             
    class Environmenttab(ProvisionEnvironment):
        '''Environment tab'''
        _add_button_locator = (
                By.CSS_SELECTOR,
                "div#buttons_on > ul#form_buttons > li > img[alt='Add']")
            
        def fill_environment_tab(self, host_name, datastore_name):
            '''Provisioning form - Environment tab'''
            self.select_dropdown("Default", *self._datacenter_select_locator)
            self._wait_for_results_refresh()
            self.select_dropdown("test_cluster", *self._cluster_select_locator)
            self._wait_for_results_refresh()
            self.select_dropdown("Default for Cluster test_cluster",
                 *self._resource_pool_select_locator)
            self._wait_for_results_refresh()
            print host_name
            print datastore_name
            self.fill_fields(host_name, datastore_name)
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._add_button_locator).click()
            self._wait_for_results_refresh()
            time.sleep(5)
            return CatalogItems.NewCatalogItem(self.testsetup)
             
    class NewCatalogBundle(Provision):
        '''CatalogBundle page'''
        _bundlename_field = (By.CSS_SELECTOR, "input[name='name']")
        _bundledesc_field = (By.CSS_SELECTOR, "input[name='description']")
        _bundledisplay_checkbox = (By.CSS_SELECTOR, "input[name='display']")
        _bundle_select_catalog = (By.CSS_SELECTOR, "select#catalog_id")
        _bundle_select_dialog = (By.CSS_SELECTOR, "select#dialog_id")
        _bundle_cost_field = (By.CSS_SELECTOR, "input[name='provision_cost']")
        _resource_locator = (By.CSS_SELECTOR, "select#resource_id")
        _add_button = (By.CSS_SELECTOR,
                "div#buttons_on > ul#form_buttons > li > img[alt='Add']")
        _edit_button = (By.CSS_SELECTOR,
                "div#buttons_on > ul#form_buttons > li > img[alt='Save Changes']")
        
        @property
        def tabbutton_region(self):
            '''tab buttons'''
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = (
                    By.CSS_SELECTOR, "div#st_form_tabs > ul > li"))
         
        def fill_bundle_basic_info(self, name, desc, catalog, dialog, cost):
            '''Fill bundle basic info page'''
            self.selenium.find_element(*self._bundledisplay_checkbox).click()
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._bundlename_field).send_keys(name)
            self.selenium.find_element(*self._bundledesc_field).send_keys(desc)
            self.select_dropdown(catalog, *self._bundle_select_catalog)
            self._wait_for_results_refresh()
            self.select_dropdown(dialog, *self._bundle_select_dialog)
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._bundle_cost_field).send_keys(cost)
            
        def click_on_resources_tab(self):
            '''Click on resources tab'''
            time.sleep(5)
            self.tabbutton_region.tabbutton_by_name('Resources').click()
            self._wait_for_results_refresh()
            return self 
        
        def click_on_add_btn(self):
            '''Click on add catalog bundle btn'''
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._add_button).click()
            self._wait_for_results_refresh()
            return self 
        
        def click_on_edit_save_btn(self):
            '''Click on edit catalog bundle btn'''
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._edit_button).click()
            self._wait_for_results_refresh()
            return self 
        
        def select_catalog_item_and_add(self, catalog_item_name):
            '''select catalog item and add and save bundle'''
            self.select_dropdown(catalog_item_name, *self._resource_locator)
            self.click_on_add_btn()
            return self   
        
        def select_catalog_item_and_edit(self, catalog_item_name):
            '''select catalog item and edit and save bundle'''
            self.select_dropdown(catalog_item_name, *self._resource_locator)
            self.click_on_edit_save_btn()
            return self   