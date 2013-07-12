

import random
import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized") 
class TestChargeback:
    _compute_chargeback_list = []
    _storage_chargeback_list = []

    def test_add_new_compute_chargeback(self, mozwebqa, home_page_logged_in, random_string):
        #Add a new Compute Chargeback
        home_pg = home_page_logged_in
        chargeback_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Chargeback").click()
        #Assert.true(chargeback_pg.is_the_current_page)
        rates_pg = chargeback_pg.click_on_rates()
        compute_pg = rates_pg.click_on_compute()
        add_compute_chargeback_pg = compute_pg.click_on_add_new_chargeback_rate()
        compute_chargeback_description = random_string
        self._compute_chargeback_list.append(random_string)
        #Edit to change the Details of the  Compute Chargeback
        Description = compute_chargeback_description
        Alloc_CPU = 1000 
        Alloc_CPU_per_time = "Daily"
        Used_CPU = ''
        Used_CPU_per_time = ''
        Disk_IO = 10
        Disk_IO_per_time = "Daily"
        Fixed_1 = 100
        Fixed_1_per_time = "Monthly"
        Fixed_2 = 200
        Fixed_2_per_time = "Daily"
        Alloc_Mem = 10000
        Alloc_Mem_per_time = "Monthly"
        Used_Mem = 4000
        Used_Mem_per_time = "Weekly"
        Net_IO = 6000
        Net_IO_per_time = "Weekly"
        
        add_fields = add_compute_chargeback_pg.fill_data(Description, Alloc_CPU, Alloc_CPU_per_time, Used_CPU, Used_CPU_per_time, Disk_IO, Disk_IO_per_time, Fixed_1, Fixed_1_per_time, Fixed_2, Fixed_2_per_time, Alloc_Mem, Alloc_Mem_per_time, Used_Mem, Used_Mem_per_time, Net_IO, Net_IO_per_time)
        add_compute_chargeback = add_compute_chargeback_pg.click_on_add()
        Assert.true(compute_pg.flash.message.startswith('Chargeback Rate "%s" was added' %compute_chargeback_description))
        #cancel_add_compute_chargeback = add_compute_chargeback_pg.click_on_cancel() 
        
        
    def test_add_new_storage_chargeback(self, mozwebqa, home_page_logged_in, random_string):
        #Add a new Storage Chargeback
        home_pg = home_page_logged_in
        chargeback_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Chargeback").click()
        Assert.true(chargeback_pg.is_the_current_page)
        rates_pg = chargeback_pg.click_on_rates()
        storage_pg = rates_pg.click_on_storage()
        add_storage_chargeback_pg = storage_pg.click_on_add_new_chargeback_rate()
        storage_chargeback_description = random_string
        self._storage_chargeback_list.append(random_string)
        #Edit to change the Details of the Storage Chargeback
        Description = storage_chargeback_description
        Fixed_1 = ''
        Fixed_1_per_time = ''
        Fixed_2 = 4000
        Fixed_2_per_time = "Monthly"
        Alloc_Disk_Storage = 2000
        Alloc_Disk_Storage_per_time = "Daily"
        Used_Disk_Storage = 6000
        Used_Disk_Storage_per_time = "Daily"

        add_fields = add_storage_chargeback_pg.fill_data(Description, Fixed_1, Fixed_1_per_time, Fixed_2, Fixed_2_per_time, Alloc_Disk_Storage, Alloc_Disk_Storage_per_time, Used_Disk_Storage, Used_Disk_Storage_per_time)
        add_storage_chargeback = add_storage_chargeback_pg.click_on_add()
        Assert.true(storage_pg.flash.message.startswith('Chargeback Rate "%s" was added' %storage_chargeback_description))
        #cancel_add_storage_chargeback = add_storage_chargeback_pg.click_on_cancel()

    def test_edit_compute_chargeback(self, mozwebqa, home_page_logged_in, random_string):
        #Edit Compute Chargeback
        home_pg = home_page_logged_in
        chargeback_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Chargeback").click()
        Assert.true(chargeback_pg.is_the_current_page)
        rates_pg = chargeback_pg.click_on_rates()
        compute_pg = rates_pg.click_on_compute()
        existing_chargeback = self._compute_chargeback_list[0]
        new_description = random_string
        self._compute_chargeback_list.remove(self._compute_chargeback_list[0])
        self._compute_chargeback_list.append(new_description)
        selected_chargeback_pg = compute_pg.click_on_existing_chargeback(existing_chargeback)
        #remove_selected_chargeback_pg = selected_chargeback_pg.click_on_remove()
        edit_selected_chargeback_pg = selected_chargeback_pg.click_on_edit()

        #Edit to change the Details of the  Compute Chargeback
        Description = new_description
        Alloc_CPU = 1000 
        Alloc_CPU_per_time = "Daily"
        Used_CPU = 10000 
        Used_CPU_per_time = "Weekly"
        Disk_IO = 100
        Disk_IO_per_time = "Daily"
        Fixed_1 = ''
        Fixed_1_per_time = ''
        Fixed_2 = ''
        Fixed_2_per_time = ''
        Alloc_Mem = 10000
        Alloc_Mem_per_time = "Monthly"
        Used_Mem = 6000
        Used_Mem_per_time = "Weekly"
        Net_IO = 10000
        Net_IO_per_time = "Monthly"
        
        add_fields = edit_selected_chargeback_pg.fill_data(Description, Alloc_CPU, Alloc_CPU_per_time, Used_CPU, Used_CPU_per_time, Disk_IO, Disk_IO_per_time, Fixed_1, Fixed_1_per_time, Fixed_2, Fixed_2_per_time, Alloc_Mem, Alloc_Mem_per_time, Used_Mem, Used_Mem_per_time, Net_IO, Net_IO_per_time)
        save_edited_chargeback = edit_selected_chargeback_pg.click_on_save()
        Assert.true(compute_pg.flash.message.startswith('Chargeback Rate "%s" was saved' %new_description))
        #cancel_changed = edit_selected_chargeback_pg.click_on_cancel()
        #reset_selected_chargeback = edit_selected_chargeback_pg.click_on_reset()

    def test_edit_storage_chargeback(self, mozwebqa, home_page_logged_in, random_string):
        home_pg = home_page_logged_in
        #Edit Storage Chargeback
        chargeback_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Chargeback").click()
        Assert.true(chargeback_pg.is_the_current_page)
        rates_pg = chargeback_pg.click_on_rates()
        storage_pg = rates_pg.click_on_storage()
        existing_chargeback = self._storage_chargeback_list[0]
        new_description = random_string
        self._storage_chargeback_list.remove(self._storage_chargeback_list[0])
        self._storage_chargeback_list.append(new_description)
        selected_chargeback_pg = storage_pg.click_on_existing_chargeback(existing_chargeback)
        #remove_selected_chargeback_pg = selected_chargeback_pg.click_on_remove()
        edit_selected_chargeback_pg = selected_chargeback_pg.click_on_edit()

        #Edit to change the Details of the Storage Chargeback
        Description = new_description
        Fixed_1 = 10000
        Fixed_1_per_time = "Weekly"
        Fixed_2 = 8000
        Fixed_2_per_time = "Monthly"
        Alloc_Disk_Storage = 400
        Alloc_Disk_Storage_per_time = "Hourly"
        Used_Disk_Storage = ''
        Used_Disk_Storage_per_time = ''

        add_fields = edit_selected_chargeback_pg.fill_data(Description, Fixed_1, Fixed_1_per_time, Fixed_2, Fixed_2_per_time, Alloc_Disk_Storage, Alloc_Disk_Storage_per_time, Used_Disk_Storage, Used_Disk_Storage_per_time)
        save_edited_chargeback = edit_selected_chargeback_pg.click_on_save()
        Assert.true(storage_pg.flash.message.startswith('Chargeback Rate "%s" was saved' %new_description))
        #cancel_changed = edit_selected_chargeback_pg.click_on_cancel()
        #reset_selected_chargeback = edit_selected_chargeback_pg.click_on_reset()

    def test_delete_compute_chargeback(self, mozwebqa, home_page_logged_in):
        #Delete Compute Chargeback
        home_pg = home_page_logged_in
        chargeback_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Chargeback").click()
        Assert.true(chargeback_pg.is_the_current_page)
        rates_pg = chargeback_pg.click_on_rates()
        compute_pg = rates_pg.click_on_compute()
        while len(self._compute_chargeback_list) > 0:
            existing_chargeback = self._compute_chargeback_list[len(self._compute_chargeback_list) - 1]
            selected_chargeback_pg = compute_pg.click_on_existing_chargeback(existing_chargeback)
            compute_pg = selected_chargeback_pg.click_on_remove()
            Assert.true(compute_pg.flash.message.startswith('The selected Chargeback Rate was deleted'))
            self._compute_chargeback_list.pop()

    def test_delete_storage_chargeback(self, mozwebqa, home_page_logged_in):
        #Delete Storage Chargeback
        home_pg = home_page_logged_in
        chargeback_pg = home_pg.header.site_navigation_menu("Virtual Intelligence").sub_navigation_menu("Chargeback").click()
        Assert.true(chargeback_pg.is_the_current_page)
        rates_pg = chargeback_pg.click_on_rates()
        storage_pg = rates_pg.click_on_storage()
        while len(self._storage_chargeback_list) > 0:
            existing_chargeback = self._storage_chargeback_list[len(self._storage_chargeback_list) - 1]
            selected_chargeback_pg = storage_pg.click_on_existing_chargeback(existing_chargeback)
            storage_pg = selected_chargeback_pg.click_on_remove()
            Assert.true(storage_pg.flash.message.startswith('The selected Chargeback Rate was deleted'))
            self._storage_chargeback_list.pop()

