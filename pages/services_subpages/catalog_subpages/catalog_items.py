'''Created on July 25, 2013

@author: Shveta
'''
from pages.base import Base
from pages.page import Page
from selenium.webdriver.common.by import By
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

    def add_new_catalog_item(self):
        '''click on Configuration and then Add new catalog item btn'''
        self.click_on_catalog_item("All Catalog Items")
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._add_catalogitem_button_locator).click()
        return CatalogItems.NewCatalogItem(self.testsetup)

    def add_new_catalog_bundle(self):
        '''Click on Configuration and then add new bundle btn'''
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._add_catalogbundle_button_locator).click()
        return CatalogItems.NewCatalogBundle(self.testsetup)

    def delete_catalog_item(self):
        '''Delete catalog'''
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._del_catalog_item_locator).click()
        self.handle_popup()
        self._wait_for_results_refresh()
        return CatalogItems(self.testsetup)

    def edit_catalog_bundle(self):
        '''Delete catalog'''
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._edit_catalog_bundle_locator).click()
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
        _add_button_locator = (By.CSS_SELECTOR,
                    "div#buttons_on > ul#form_buttons > li > img[alt='Add']")

        @property
        def headertab_region(self):
            '''tab buttons'''
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(
                self.testsetup, locator_override=(By.CSS_SELECTOR, "div#st_form_tabs > ul > li"))

        @property
        def tabbutton_region(self):
            '''Return the tab button region'''
            from pages.regions.tabbuttons import TabButtons
            from pages.services_subpages.provision import ProvisionTabButtonItem
            return TabButtons(self.testsetup,
                locator_override=self._tab_button_locator,
                cls=ProvisionTabButtonItem)

        def click_on_request_info_tab(self):
            '''Click on Reuqest info tab'''
            self.headertab_region.tabbutton_by_name('Request Info').click()
            self._wait_for_results_refresh()
            return CatalogItems.NewCatalogItem(self.testsetup)

        def choose_catalog_item_type(self, catalog_item_type):
            '''Choose catalog item type'''
            self.select_dropdown(catalog_item_type, *self._catalog_item_type)
            self._wait_for_results_refresh()
            return CatalogItems.NewCatalogItem(self.testsetup)

        def fill_basic_info(self, name, desc, catalog, dialog):
            self.get_element(*self._display_checkbox).click()
            self._wait_for_visible_element(*self._select_catalog)
            self.get_element(*self._name_field).send_keys(name)
            time.sleep(2)
            self.get_element(*self._desc_field).send_keys(desc)
            self._wait_for_results_refresh()
            self.select_dropdown(catalog, *self._select_catalog)
            self._wait_for_results_refresh()
            self.select_dropdown(dialog, *self._select_dialog)
            self._wait_for_results_refresh()
            return CatalogItems.ProvisionEntryPoint(self.testsetup)

        def fill_catalog_tab(self,
            template_name,
            provision_type,
            pxe_server,
            server_image,
            provider,
            no_of_vm,
            vm_name):
            '''Provisioning form - catalog tab'''
            for item in ProvisionCatalog(self).catalog_list.items:
                if item.name == template_name and item.provider == provider:
                    item.click()
                    break
            self._wait_for_results_refresh()
            vm_desc = None
            ProvisionCatalog(self).fill_fields(provision_type, pxe_server,
                server_image, no_of_vm, vm_name, vm_desc)
            return CatalogItems(self.testsetup)

        def save_catalog_item(self):
            '''Save'''
            self._wait_for_visible_element(*self._add_button_locator)
            self.get_element(*self._add_button_locator).click()
            #time.sleep(5)
            self._wait_for_results_refresh()
            return self

    class ProvisionEntryPoint(Page):
        '''Provision Entry  Point'''
        _provisioning_entry_point = (
            By.CSS_SELECTOR, "input[id='fqname']")
        _apply_btn = (
            By.CSS_SELECTOR, "ul#form_buttons > li > a > img[alt='Apply']")
        _tag_tree_locator = (
            By.CSS_SELECTOR, 'div#automate_tree_box > div')

        @property
        def tag_tree(self):
            '''Tree'''
            from pages.regions.tree import LegacyTree
            return LegacyTree(self.testsetup,
                    self.get_element(*self._tag_tree_locator))

        def fill_provisioning_entry_point(self, node1):
            '''Select node in tree'''
            self.get_element(*self._provisioning_entry_point).click()
            for handle in self.selenium.window_handles:
                self.selenium.switch_to_window(handle)
                self.tag_tree.find_node_by_name(node1).twisty.expand()
                self.tag_tree.find_node_by_name(node1).children[3].click()
                self._wait_for_results_refresh()
                self._wait_for_visible_element(*self._apply_btn)
                self.get_element(*self._apply_btn).click()
                time.sleep(5)
            self._wait_for_results_refresh()
            return CatalogItems.NewCatalogItem(self.testsetup)

    class Environmenttab(ProvisionEnvironment):
        '''Environment tab'''

        def fill_environment_tab(self, datacenter, cluster,
                                 resource_pool, host_name,
                                 datastore_name):
            '''Provisioning form - Environment tab'''
            self.select_dropdown(datacenter, *self._datacenter_select_locator)
            self._wait_for_results_refresh()
            self.select_dropdown(cluster, *self._cluster_select_locator)
            self._wait_for_results_refresh()
            self.select_dropdown(resource_pool,
                 *self._resource_pool_select_locator)
            self._wait_for_results_refresh()
            self.fill_fields(host_name, datastore_name)
            self._wait_for_results_refresh()
            return CatalogItems(self.testsetup)

    class NewCatalogBundle(Provision):
        '''CatalogBundle page'''
        _bundlename_field = (By.CSS_SELECTOR, "input[name='name']")
        _bundledesc_field = (By.CSS_SELECTOR, "input[name='description']")
        _bundledisplay_checkbox = (By.CSS_SELECTOR, "input[name='display']")
        _bundle_select_catalog = (By.CSS_SELECTOR, "select#catalog_id")
        _bundle_select_dialog = (By.CSS_SELECTOR, "select#dialog_id")
        _resource_locator = (By.CSS_SELECTOR, "select#resource_id")
        _add_button = (By.CSS_SELECTOR,
            "div#buttons_on > ul#form_buttons > li > img[alt='Add']")
        _edit_button = (By.CSS_SELECTOR,
            "div#buttons_on > ul#form_buttons > li > img[alt='Save Changes']")

        @property
        def tabbutton_region(self):
            '''tab buttons'''
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override=(
                By.CSS_SELECTOR, "div#st_form_tabs > ul > li"))

        def fill_bundle_basic_info(self, name, desc, catalog, dialog):
            self.get_element(*self._bundledisplay_checkbox).click()
            self._wait_for_results_refresh()
            self._wait_for_visible_element(*self._bundle_select_catalog)
            self.get_element(*self._bundlename_field).send_keys(name)
            self.get_element(*self._bundledesc_field).send_keys(desc)
            self.select_dropdown(catalog, *self._bundle_select_catalog)
            self._wait_for_results_refresh()
            self.select_dropdown(dialog, *self._bundle_select_dialog)
            self._wait_for_results_refresh()
            return self

        def click_on_resources_tab(self):
            '''Click on resources tab'''
            time.sleep(5)
            self.tabbutton_region.tabbutton_by_name('Resources').click()
            self._wait_for_results_refresh()
            return self

        def click_on_add_btn(self):
            self._wait_for_results_refresh()
            self.get_element(*self._add_button).click()
            self._wait_for_results_refresh()
            return self

        def click_on_edit_save_btn(self):
            '''Click on edit catalog bundle btn'''
            self._wait_for_results_refresh()
            self.get_element(*self._edit_button).click()
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
