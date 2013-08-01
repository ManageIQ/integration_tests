from pages.base import Base
from selenium.webdriver.common.by import By
from pages.configuration_subpages.settings_subpages.zone_settings import ZoneSettings
from pages.regions.list import ListRegion, ListItem
from pages.regions.checkboxtree import LegacyCheckbox
from pages.regions.twisty import LegacyTwisty

class RegionSettings(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _zones_button = (By.CSS_SELECTOR, "div[title='View Zones']")

    @property
    def tab_buttons(self):
        from pages.regions.tabbuttons import TabButtons
        return TabButtons(self.testsetup, locator_override = (By.CSS_SELECTOR, "div#ops_tabs > ul > li"))

    def click_on_cap_and_util(self):
        cap_and_util_pg = self.tab_buttons.tabbutton_by_name("C & U Collection")
        cap_and_util_pg.click()
        self._wait_for_results_refresh()
        return RegionSettings.CapAndUtil(self.testsetup)

    class CapAndUtil(Base):
        _collect_all_clusters_checkbox_locator = (By.CSS_SELECTOR, "input#all_clusters")
        _collect_all_datastores_checkbox_locator = (By.CSS_SELECTOR, "input#all_storages")
        _save_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Save Changes']")
        _reset_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Reset Changes']")
        _check_all_clusters_checkbox_locator = (By.CSS_SELECTOR, "input#cl_toggle")
        _check_all_datastores_checkbox_locator = (By.CSS_SELECTOR, "input#ds_toggle")

        @property
        def cluster_checkbox(self):
            return self.selenium.find_element(*self._collect_all_clusters_checkbox_locator)

        @property 
        def datastore_checkbox(self):
            return self.selenium.find_element(*self._collect_all_datastores_checkbox_locator)

        @property 
        def save_button(self):
            return self.selenium.find_element(*self._save_button_locator)

        @property
        def reset_button(self):
            return self.selenium.find_element(*self._reset_button_locator)

        @property
        def check_all_clusters_checkbox(self):
            return self.selenium.find_element(*self._check_all_clusters_checkbox_locator)

        @property
        def check_all_datastores_checkbox(self):
            return self.selenium.find_element(*self._check_all_datastores_checkbox_locator)

        @property
        def cluster_list(self):
            _root_item_locator = (By.CSS_SELECTOR, "div#clhosts_treebox > div > table > tbody")
            return ListRegion(self.testsetup, self.get_element(*_root_item_locator), self.ClusterItem)

        @property
        def datastore_list(self):
            _root_item_locator = (By.CSS_SELECTOR, "div#datastores_treebox > div > table > tbody")
            return ListRegion(self.testsetup, self.get_element(*_root_item_locator), self.DatastoreItem)

        def check_all_clusters(self):
            if(self.cluster_checkbox.get_attribute("checked") != "true"):
                self.cluster_checkbox.click()
                self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def uncheck_all_clusters(self):
            if(self.cluster_checkbox.get_attribute("checked") == "true"):
                self.cluster_checkbox.click()
                self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)            
        
        def check_specific_cluster(self, cluster_name):
            cluster = self.cluster_by_name(cluster_name)
            cluster.check()
            #self._wait_for_results_refresh() 
            return RegionSettings.CapAndUtil(self.testsetup)

        def uncheck_specific_cluster(self, cluster_name):
            cluster = self.cluster_by_name(cluster_name)
            cluster.uncheck()
            #self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def cluster_by_name(self, cluster_name):
            cluster_items = self.cluster_list.items
            for item in range(len(cluster_items)):
                if(item%2 == 0 and item != 0):
                    cluster_items[item].expand()
            return cluster_items[[item for item in range(len(cluster_items)) if cluster_items[item].name == cluster_name][0]]

        def check_all_datastores(self):
            if(self.datastore_checkbox.get_attribute("checked") != "true"):
                self.datastore_checkbox.click()
                self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def uncheck_all_datastores(self):
            if(self.datastore_checkbox.get_attribute("checked") == "true"):
                self.datastore_checkbox.click()
                self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def check_specific_datastore(self, datastore_name):
            datastore = self.datastore_by_name(datastore_name)
            datastore.check()
            #self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def uncheck_specific_datastore(self, datastore_name):
            datastore = self.datastore_by_name(datastore_name)
            datastore.uncheck()
            #self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def datastore_by_name(self, datastore_name):
            datastore_items = self.datastore_list.items
            return datastore_items[[item for item in range(len(datastore_items)) if datastore_items[item].name == datastore_name][0]]

        def click_on_save(self):
            self._wait_for_visible_element(*self._save_button_locator)
            self.save_button.click()
            self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        def click_on_reset(self):
            self._wait_for_visible_element(*self._reset_button_locator)
            self.reset_button.click()
            self._wait_for_results_refresh()
            return RegionSettings.CapAndUtil(self.testsetup)

        class ClusterItem(ListItem, LegacyCheckbox, LegacyTwisty):
            @property
            def name(self):
                return self._item_data[3].text.encode('utf-8')

        class DatastoreItem(ListItem, LegacyCheckbox, LegacyTwisty):
            @property
            def name(self):
                return self._item_data[3].text.encode('utf-8')
    

            
