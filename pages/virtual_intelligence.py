# -*- coding: utf-8 -*-


import time
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class VirtualIntelligence(Base):
    @property
    def submenus(self):
        return {"report"    : VirtualIntelligence.Reports,
                "chargeback"    : VirtualIntelligence.Chargeback,
                }

    class Reports(Base):
        _page_title = 'CloudForms Management Engine: Reports'

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)

        def click_on_import_export(self):
            self.accordion.accordion_by_name("Import/Export").click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.ImportExport(self.testsetup)

    class ImportExport(Reports):
        _reports_import_field = (By.ID, "upload_file")
        _upload_button = (By.ID, "upload_atags")
        _overwrite_checkbox = (By.ID, "overwrite")

        @property
        def upload(self):
            return self.selenium.find_element(*self._upload_button)
        
        def check_overwrite_box(self):
            if not self.selenium.find_element(*self._overwrite_checkbox).is_selected():
                self.selenium.find_element(*self._overwrite_checkbox).click()

        def click_on_upload(self):
            self.upload.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Reports(self.testsetup)

        def import_reports(self, import_reports_file, overwrite = True):
            self._wait_for_results_refresh()
            if overwrite:
                self.check_overwrite_box()
            self.selenium.find_element(*self._reports_import_field).send_keys(import_reports_file)
            return self.click_on_upload()

    class Chargeback(Base):
        _page_title = 'CloudForms Management Engine: Chargeback'

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup, TreeAccordionItem)
    
        def click_on_rates(self):
            self.accordion.accordion_by_name("Rates").click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Rates(self.testsetup)
    
    class Rates(Base):
        _compute_button = (By.CSS_SELECTOR, "tr[title='Compute']")
        _storage_button = (By.CSS_SELECTOR, "tr[title='Storage']")
        
        @property
        def compute(self):
            return self.selenium.find_element(*self._compute_button)
        
        @property
        def storage(self):
            return self.selenium.find_element(*self._storage_button)

        def click_on_compute(self):
            self.compute.click()            
            self._wait_for_results_refresh()
            _chargeback_type = "Compute"
            return VirtualIntelligence.ComputeStorage(_chargeback_type, self.testsetup)

        def click_on_storage(self):
            self.storage.click()
            self._wait_for_results_refresh()
            _chargeback_type = "Storage"
            return VirtualIntelligence.ComputeStorage(_chargeback_type, self.testsetup)
           
    class ComputeStorage(Base):
        _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
        _add_new_chargeback_rate_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a new Chargeback Rate']")
        _existing_chargeback_button_locator_template =  "td[title='%s']"       

        @property
        def configuration_button(self):
            return self.selenium.find_element(*self._configuration_button_locator)        

        @property
        def add_button(self):
            return self.selenium.find_element(*self._add_new_chargeback_rate_button_locator)
        
        def __init__(self, chargeback_type, *args, **kwargs):
            super(VirtualIntelligence.ComputeStorage, self).__init__(*args, **kwargs)
            self._chargeback_type = chargeback_type

        def get_chargeback_by_name(self, existing_chargeback_name):
            return self.selenium.find_element(By.CSS_SELECTOR, self._existing_chargeback_button_locator_template % existing_chargeback_name)

        def click_on_add_new_chargeback_rate(self):
            ActionChains(self.selenium).click(self.configuration_button).click(self.add_button).perform()
            if(self._chargeback_type == "Compute"):
                return VirtualIntelligence.AddEditComputeChargeback(self.testsetup)
            else:
                return VirtualIntelligence.AddEditStorageChargeback(self.testsetup)

        def click_on_existing_chargeback(self, existing_chargeback_name):
            existing_chargeback = self.get_chargeback_by_name(existing_chargeback_name)
            existing_chargeback.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.ExistingChargeback(self._chargeback_type, self.testsetup)


    class AddEditComputeChargeback(Base):
        _description_edit_field_locator = (By.CSS_SELECTOR, "input#description")
        _save_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Save Changes']")
        _reset_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Reset Changes']")
        _add_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")
        _cancel_button_locator = (By.CSS_SELECTOR, "div#buttons_off > ul#form_buttons > li > img[title='Cancel']")
        _alloc_cpu_edit_field_locator = (By.CSS_SELECTOR, "input#rate_0")
        _alloc_cpu_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_0")
        _used_cpu_edit_field_locator = (By.CSS_SELECTOR, "input#rate_1")
        _used_cpu_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_1")
        _disk_io_edit_field_locator = (By.CSS_SELECTOR, "input#rate_2")
        _disk_io_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_2")
        _fixed_1_edit_field_locator = (By.CSS_SELECTOR, "input#rate_3")
        _fixed_1_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_3")
        _fixed_2_edit_field_locator = (By.CSS_SELECTOR, "input#rate_4")
        _fixed_2_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_4")
        _alloc_mem_edit_field_locator = (By.CSS_SELECTOR, "input#rate_5")
        _alloc_mem_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_5")
        _used_mem_edit_field_locator = (By.CSS_SELECTOR, "input#rate_6")
        _used_mem_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_6")
        _net_io_edit_field_locator = (By.CSS_SELECTOR, "input#rate_7")
        _net_io_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_7")


        @property
        def add_button(self):
            return self.get_element(*self._add_button_locator)

        @property
        def save_button(self):
            return self.get_element(*self._save_button_locator)

        @property
        def cancel_button(self):
            return self.get_element(*self._cancel_button_locator)

        @property
        def description_input(self):
            return self.get_element(*self._description_edit_field_locator)
        
        @property
        def alloc_cpu_input(self):
            return self.get_element(*self._alloc_cpu_edit_field_locator)

        @property
        def used_cpu_input(self):
            return self.get_element(*self._used_cpu_edit_field_locator)

        @property
        def used_io_input(self):
            return self.get_element(*self._used_cpu_edit_field_locator)

        @property
        def disk_io_input(self):
            return self.get_element(*self._disk_io_edit_field_locator)

        @property
        def fixed_1_input(self):
            return self.get_element(*self._fixed_1_edit_field_locator)

        @property
        def fixed_2_input(self):
            return self.get_element(*self._fixed_2_edit_field_locator)

        @property
        def alloc_mem_input(self):
            return self.get_element(*self._alloc_mem_edit_field_locator)

        @property
        def used_mem_input(self):
            return self.get_element(*self._used_mem_edit_field_locator)

        @property
        def net_io_input(self):
            return self.get_element(*self._net_io_edit_field_locator)

        def click_on_add(self):
            time.sleep(1)
            self.add_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def click_on_cancel(self):
            time.sleep(1)
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)
    
        def click_on_save(self):
            time.sleep(1)
            self.save_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)
        
        def click_on_reset(self):
            time.sleep(1)
            self.reset_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def fill_data(self, description, alloc_cpu, alloc_cpu_per_time, used_cpu, used_cpu_per_time,  disk_io, disk_io_per_time,  fixed_1, fixed_1_per_time,  fixed_2, fixed_2_per_time, alloc_mem, alloc_mem_per_time,  used_mem, used_mem_per_time, net_io, net_io_per_time):
            
            #Fill in the Description Field
            if(description):
                self.description_input.clear()
                self.description_input.send_keys(description)
            
            #Fill in the Allocated CPU Fields
            if(alloc_cpu):
                self.alloc_cpu_input.clear()
                self.alloc_cpu_input.send_keys(alloc_cpu)
                self.select_dropdown(alloc_cpu_per_time, *self._alloc_cpu_per_time_edit_field_locator)

            #Fill in the Used CPU Fields
            if(used_cpu):
                self.used_cpu_input.clear()
                self.used_cpu_input.send_keys(used_cpu)
                self.select_dropdown(used_cpu_per_time, *self._used_cpu_per_time_edit_field_locator)

            #Fill in the Disk IO Fields
            if(disk_io):
                self.disk_io_input.clear()
                self.disk_io_input.send_keys(disk_io)
                self.select_dropdown(disk_io_per_time, *self._disk_io_per_time_edit_field_locator)

            #Fill in the Fixed 1 Fields
            if(fixed_1):
                self.fixed_1_input.clear()
                self.fixed_1_input.send_keys(fixed_1)
                self.select_dropdown(fixed_1_per_time, *self._fixed_1_per_time_edit_field_locator)

            #Fill in the Fixed 2 Fields
            if(fixed_2):
                self.fixed_2_input.clear()
                self.fixed_2_input.send_keys(fixed_2)
                self.select_dropdown(fixed_2_per_time, *self._fixed_2_per_time_edit_field_locator)

            #Fill in the Allocated Memory Fields
            if(alloc_mem):
                self.alloc_mem_input.clear()
                self.alloc_mem_input.send_keys(alloc_mem)
                self.select_dropdown(alloc_mem_per_time, *self._alloc_mem_per_time_edit_field_locator)

            #Fill in the Used Memory Fields
            if(used_mem):
                self.used_mem_input.clear()
                self.used_mem_input.send_keys(used_mem)
                self.select_dropdown(used_mem_per_time, *self._used_mem_per_time_edit_field_locator)

            #Fill in the Network IO Fields
            if(net_io):
                self.net_io_input.clear()
                self.net_io_input.send_keys(net_io)
                self.select_dropdown(net_io_per_time, *self._net_io_per_time_edit_field_locator)

    class AddEditStorageChargeback(Base):
        _description_edit_field_locator = (By.CSS_SELECTOR, "input#description")
        _add_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")
        _save_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Save Changes']")
        _reset_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Reset Changes']")
        _cancel_button_locator = (By.CSS_SELECTOR, "div#buttons_off > ul#form_buttons > li > img[title='Cancel']")
        _fixed_1_edit_field_locator = (By.CSS_SELECTOR, "input#rate_0")
        _fixed_1_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_0")
        _fixed_2_edit_field_locator = (By.CSS_SELECTOR, "input#rate_1")
        _fixed_2_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_1")
        _alloc_disk_storage_edit_field_locator = (By.CSS_SELECTOR, "input#rate_2")
        _alloc_disk_storage_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_2")
        _used_disk_storage_edit_field_locator = (By.CSS_SELECTOR, "input#rate_3")
        _used_disk_storage_per_time_edit_field_locator = (By.CSS_SELECTOR, "select#per_time_3")

        @property
        def add_button(self):
            return self.get_element(*self._add_button_locator)

        @property
        def cancel_button(self):
            return self.get_element(*self._cancel_button_locator)

        @property
        def save_button(self):
            return self.get_element(*self._save_button_locator)

        @property
        def description_input(self):
            return self.get_element(*self._description_edit_field_locator)

        @property
        def fixed_1_input(self):
            return self.get_element(*self._fixed_1_edit_field_locator)

        @property
        def fixed_2_input(self):
            return self.get_element(*self._fixed_2_edit_field_locator)
        
        @property
        def alloc_disk_storage_input(self):
            return self.get_element(*self._alloc_disk_storage_edit_field_locator)

        @property
        def used_disk_storage_input(self):
            return self.get_element(*self._used_disk_storage_edit_field_locator) 

        def click_on_add(self):
            time.sleep(1)
            self.add_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def click_on_cancel(self):
            time.sleep(1)
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def click_on_save(self):
            time.sleep(1)
            self.save_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def click_on_reset(self):
            time.sleep(1)
            self.reset_button.click()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def fill_data(self, description, fixed_1, fixed_1_per_time, fixed_2, fixed_2_per_time, alloc_disk_storage, alloc_disk_storage_per_time, used_disk_storage, used_disk_storage_per_time):
            
            #Fill in the Description Field
            if(description):
                self.description_input.clear()
                self.description_input.send_keys(description)

            #Fill in the Fixed 1 Fields
            if(fixed_1):
                self.fixed_1_input.clear()
                self.fixed_1_input.send_keys(fixed_1)
                self.select_dropdown(fixed_1_per_time, *self._fixed_1_per_time_edit_field_locator)

            #Fill in the Fixed 2 Fields
            if(fixed_2):
                self.fixed_2_input.clear()
                self.fixed_2_input.send_keys(fixed_2)
                self.select_dropdown(fixed_2_per_time, *self._fixed_2_per_time_edit_field_locator)

            #Fill in the Allocated Disk Storage Fields
            if(alloc_disk_storage):
                self.alloc_disk_storage_input.clear()
                self.alloc_disk_storage_input.send_keys(alloc_disk_storage)
                self.select_dropdown(alloc_disk_storage_per_time, *self._alloc_disk_storage_per_time_edit_field_locator)

            #Fill in the Used Disk Storage Fields
            if(used_disk_storage):
                self.used_disk_storage_input.clear()
                self.used_disk_storage_input.send_keys(used_disk_storage)
                self.select_dropdown(used_disk_storage_per_time, *self._used_disk_storage_per_time_edit_field_locator)
 
    class ExistingChargeback(Base):
        _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
        _edit_chargeback_rate_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Edit this Chargeback Rate']")
        _remove_chargeback_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Remove this Chargeback Rate from the VMDB']")
        _copy_chargeback_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title = 'Copy this Chargeback Rate']")

        @property
        def configuration_button(self):
            return self.selenium.find_element(*self._configuration_button_locator)

        @property
        def edit_button(self):
            return self.selenium.find_element(*self._edit_chargeback_rate_button_locator)

        @property
        def remove_button(self):
            return self.selenium.find_element(*self._remove_chargeback_button_locator)

        @property
        def copy_button(self):
            return self.selenium.find_element(*self._copy_chargeback_button_locator)


        def __init__(self, chargeback_type, *args, **kwargs):
            super(VirtualIntelligence.ExistingChargeback, self).__init__(*args, **kwargs)
            self._chargeback_type = chargeback_type

        def click_on_edit(self):
            ActionChains(self.selenium).click(self.configuration_button).click(self.edit_button).perform()
            self._wait_for_results_refresh()
            if(self._chargeback_type == "Compute"):
                return VirtualIntelligence.AddEditComputeChargeback(self.testsetup)
            else:
                return VirtualIntelligence.AddEditStorageChargeback(self.testsetup)

        def click_on_remove(self):
            ActionChains(self.selenium).click(self.configuration_button).click(self.remove_button).perform()
            alert = self.selenium.switch_to_alert()
            alert.accept()
            self._wait_for_results_refresh()
            return VirtualIntelligence.Chargeback(self.testsetup)

        def click_on_copy(self):
            ActionChains(self.selenium).click(self.configuration_button).click(self.copy_button).perform()
            if(self._chargeback_type == "Compute"):
                return VirtualIntelligence.AddEditComputeChargeback(self.testsetup)
            else:
                return VirtualIntelligence.AddEditStorageChargeback(self.testsetup)


