# -*- coding: utf-8 -*-

import re
import time
from pages.base import Base
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.paginator import PaginatorMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from pages.regions.list import ListRegion, ListItem
from pages.services_subpages.catalog_subpages.catalog_items import CatalogItems
from pages.services_subpages.catalog_subpages.service_catalogs import ServiceCatalogs

class Services(Base):
    @property
    def submenus(self):
        return {"services"       : Services.MyServices,
                "catalogs"       : Services.Catalogs,
                "miq_request_vm" : Service.Requests,
                "vmx"            : Services.VirtualMachines,
                }

    @property
    def is_the_current_page(self):
        '''Override for top-level menu class'''
        return self.current_subpage.is_the_current_page

    class MyServices(Base, PaginatorMixin):

        _page_title = 'CloudForms Management Engine: My Services'

    class Requests(Base, PaginatorMixin):

        _page_title = 'CloudForms Management Engine: Requests'
        _requests_table = (By.CSS_SELECTOR, "div#list_grid > div.objbox > table > tbody")
        _check_box_approved = (By.ID, "state_choice__approved")
        _check_box_denied = (By.ID, "state_choice__denied")
        _reload_button = (By.CSS_SELECTOR, "div#center_tb > div.float_left > div[title='Reload the current display']")
        _approve_this_request_button = (By.CSS_SELECTOR, "div#center_tb > div.float_left > div[title='Approve this Request']")
        _reason_text_field = (By.ID, "reason")
        _submit_button = (By.CSS_SELECTOR, "span#buttons_on > a > img[alt='Submit']")

        @property
        def requests_list(self):
            return ListRegion(
                self.testsetup,
                self.get_element(*self._requests_table),
                Services.RequestItem)

        def approve_request(self, item_number):

            self.get_element(*self._check_box_approved).click()
            self.get_element(*self._check_box_denied).click()
            self.get_element(*self._reload_button).click()
            self._wait_for_results_refresh()

            self.requests_list.items[item_number]._item_data[1].find_element_by_tag_name('img').click()
            self.selenium.find_element(*self._approve_this_request_button).click()
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._reason_text_field).send_keys("Test provisioning")
            self._wait_for_results_refresh()
            self._wait_for_visible_element(*self._submit_button)
            self.selenium.find_element(*self._submit_button).click()
            self._wait_for_results_refresh()
            return Services.Requests(self.testsetup)

    class RequestItem(ListItem):
        '''Represents a request in the list'''
        _columns = ["view_this_item", "status", "request_id", "requester", "request _type", "completed", "description", "approved_on", "created_on", "last_update", "reason", "last_message", "region"]

        @property
        def view_this_item(self):
            return self._item_data[0].text

        @property
        def status(self):
            return self._item_data[1].text

        @property
        def request_id(self):
            pass

        @property
        def requester(self):
            pass

        @property
        def request_type(self):
            pass

        @property
        def completed(self):
            pass

        @property
        def description(self):
            pass

        @property
        def approved_on(self):
            pass

        @property
        def created_on(self):
            pass

        @property
        def last_update(self):
            pass

        @property
        def reason(self):
            pass

        @property
        def last_message(self):
            pass

        @property
        def region(self):
            pass
        
        
    class Catalogs(Base):
        _page_title = 'CloudForms Management Engine: Catalogs'
           
        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            return Accordion(self.testsetup)

        def click_on_catalogs_accordion(self):
             self.accordion.accordion_by_name('Catalogs').click()
             self._wait_for_results_refresh()
             return Catalogs(self.testsetup)

        def click_on_catalog_item_accordion(self):
            self.accordion.accordion_by_name('Catalog Items').click()
            self._wait_for_results_refresh()
            return CatalogItems(self.testsetup)

        def click_on_service_catalogs_accordion(self):
            self.accordion.accordion_by_name('Service Catalogs').click()
            self._wait_for_results_refresh()
            return ServiceCatalogs(self.testsetup)

    class VmCommonComponents(Base, PaginatorMixin):

        _page_title = 'CloudForms Management Engine: Virtual Machines'

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import TreeAccordionItem
            return Accordion(self.testsetup,TreeAccordionItem)

        @property
        def history_buttons(self):
            from pages.regions.taskbar.history import HistoryButtons
            return HistoryButtons(self.testsetup)

        @property
        def view_buttons(self):
            from pages.regions.taskbar.view import ViewButtons
            return ViewButtons(self.testsetup)

        @property
        def center_buttons(self):
            from pages.regions.taskbar.center import CenterButtons
            return CenterButtons(self.testsetup)

        def refresh(self):
            """Refresh the page by clicking the refresh button that is part of the history button region.

            Note:
                Contains try/except because of page differences depending on how the page
                is loaded... mgmt_system all_vms click through (which does not have the refresh button) versus services tab > VMs
                When the refresh button is not found, a browser refresh is performed.
            """
            try:
                self.history_buttons.refresh_button.click()
                self._wait_for_results_refresh()
            except NoSuchElementException:
                self.selenium.refresh()

        @property
        def power_button(self):
            from pages.regions.taskbar.power import PowerButton
            return PowerButton(self.testsetup)

        @property
        def config_button(self):
            from pages.regions.taskbar.vm_configuration import ConfigButton
            return ConfigButton(self.testsetup)

    class VirtualMachines(VmCommonComponents):

        _provision_vms_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Request to Provision VMs']")

        @property
        def quadicon_region(self):
            return Quadicons(self.testsetup,Services.VirtualMachines.VirtualMachineQuadIconItem)

        @property
        def search(self):
            from pages.regions.search import Search
            return Search(self.testsetup)

        def _mark_icon_and_call_method(self, vm_names, op_func):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            op_func()

        def shutdown(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.shutdown )

        def shutdown_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.shutdown_and_cancel )

        def restart(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.restart )

        def restart_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.restart_and_cancel )

        def power_on(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.power_on )

        def power_on_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.power_on_and_cancel )

        def power_off(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.power_off )

        def power_off_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.power_off_and_cancel )

        def reset(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.reset )

        def reset_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.reset_and_cancel )

        def suspend(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.suspend )

        def suspend_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.power_button.suspend_and_cancel )

        def smart_state_scan(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.perform_smart_state_analysis )

        def smart_state_scan_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.perform_smart_state_analysis_and_cancel )

        def refresh_relationships(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.refresh_relationships )

        def refresh_relationships_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.refresh_relationships_and_cancel )

        def extract_running_processes(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.extract_running_processes )

        def extract_running_processes_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.extract_running_processes_and_cancel )

        #def edit_vm(self,vm_name,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox([vm_name])
        #    return Services.EditVm(self.testsetup, vm_name)

        #def set_ownership(self,vm_names,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox(vm_names)
        #    return Services.SetOwnership(self.testsetup, vm_names)

        def remove_from_vmdb(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.remove_from_vmdb )

        def remove_from_vmdb_and_cancel(self,vm_names):
            self._mark_icon_and_call_method(vm_names, self.config_button.remove_from_vmdb_and_cancel )

        def click_on_provision_vms(self):
            provision_vms_button = self.get_element(*self._provision_vms_button_locator)
            ActionChains(self.selenium).click(self.center_buttons.lifecycle_button).click(provision_vms_button).perform()
            from pages.services_subpages.provision import ProvisionStart
            return ProvisionStart(self.testsetup)

        def find_vm_page(self, vm_name = None, vm_type = None, mark_checkbox = False, load_details = False):
            found = None
            while not found:
                for quadicon in self.quadicon_region.quadicons:
                    # find exact title/type match
                    if quadicon.title == vm_name and quadicon.current_state == vm_type:
                        found = quadicon
                        break
                    # no title but first type
                    elif vm_name == None and quadicon.current_state == vm_type:
                        found = quadicon
                        break
                    # first title no type
                    elif quadicon.title == vm_name and vm_type == None:
                        found = quadicon
                        break
                    # if nothing found try turning the page
                if not found and not self.paginator.is_next_page_disabled:
                    self.paginator.click_next_page()
                elif not found and self.paginator.is_next_page_disabled:
                    raise Exception("vm("+str(vm_name)+") with type("+str(vm_type)+") could not be found")
            if found and mark_checkbox:
                found.mark_checkbox()
            if found and load_details:
                return found.click()

        def wait_for_vm_state_change(self, vm_quadicon_title, desired_state, timeout_in_minutes):
            self.find_vm_page(vm_quadicon_title,None,False)
            current_state = self.quadicon_region.get_quadicon_by_title(vm_quadicon_title).current_state
            print "Desired state: " + desired_state + "    Current state: " + current_state
            minute_count = 0
            while (minute_count < timeout_in_minutes):
                if (current_state == desired_state):
                    break
                print "Sleeping 60 seconds, iteration " + str(minute_count+1) + " of " + str(timeout_in_minutes) + ", desired state (" + desired_state+") != current state("+current_state+")"
                time.sleep(60)
                minute_count += 1
                self.refresh()
                self.find_vm_page(vm_quadicon_title,None,False)
                current_state = self.quadicon_region.get_quadicon_by_title(vm_quadicon_title).current_state
                if (minute_count==timeout_in_minutes) and (current_state != desired_state):
                    raise Exception("timeout reached("+str(timeout_in_minutes)+" minutes) before desired state (" +
                                     desired_state+") reached... current state("+current_state+")")


        class VirtualMachineQuadIconItem(QuadiconItem):
            @property
            def os(self):
                image_src = self._root_element.find_element(*self._quad_tl_locator).find_element_by_tag_name("img").get_attribute("src")
                return re.search('.+/os-(.+)\.png', image_src).group(1)

            @property
            def current_state(self):
                image_src = self._root_element.find_element(*self._quad_tr_locator).find_element_by_tag_name("img").get_attribute("src")
                return re.search('.+/currentstate-(.+)\.png',image_src).group(1)

            @property
            def vendor(self):
                image_src = self._root_element.find_element(*self._quad_bl_locator).find_element_by_tag_name("img").get_attribute("src")
                return re.search('.+/vendor-(.+)\.png', image_src).group(1)

            @property
            def snapshots(self):
                return self._root_element.find_element(*self._quad_br_locator).text

            def click(self):
                self._root_element.click()
                self._wait_for_results_refresh()
                return Services.VirtualMachineDetails(self.testsetup)


    class VirtualMachineDetails(VmCommonComponents):
        _details_locator = (By.CSS_SELECTOR, "div#textual_div")
        _set_retirement_date_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Set Retirement Dates for this VM']")
        _immediately_retire_vm_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Immediately Retire this VM']")
        _utilization_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Show Capacity & Utilization data for this VM']")

        @property
        def set_retirement_date_button(self):
            return self.selenium.find_element(*self._set_retirement_date_button_locator)

        @property
        def immediately_retire_vm_button(self):
            return self.selenium.find_element(*self._immediately_retire_vm_button_locator)


        @property
        def utilization_button(self):
            return self.selenium.find_element(*self._utilization_button_locator)
        @property
        def power_state(self):
            return self.details.get_section('Power Management').get_item('Power State').value

        @property
        def last_boot_time(self):
            return self.details.get_section('Power Management').get_item('Last Boot Time').value

        @property
        def last_pwr_state_change(self):
            return self.details.get_section('Power Management').get_item('State Changed On').value

        @property
        def details(self):
            from pages.regions.details import Details
            root_element = self.selenium.find_element(*self._details_locator)
            return Details(self.testsetup, root_element)

        def click_on_set_retirement_date(self):
            ActionChains(self.selenium).click(self.center_buttons.lifecycle_button).click(self.set_retirement_date_button).perform()
            self._wait_for_results_refresh()
            return Services.SetRetirementDate(self.testsetup)

        def click_on_immediately_retire_vm(self, cancel=False):
            ActionChains(self.selenium).click(self.center_buttons.lifecycle_button).click(self.immediately_retire_vm_button).perform()
            self.handle_popup(cancel)
            self._wait_for_results_refresh()
            return Services.VirtualMachines(self.testsetup)

        def click_on_utilization(self):
            ActionChains(self.selenium).click(self.center_buttons.monitoring_button).click(self.utilization_button).perform()
            self._wait_for_results_refresh()
            return Services.VirtualMachineUtil(self.testsetup)

        def wait_for_vm_state_change(self, desired_state, timeout_in_minutes):
            current_state = self.power_state
            print "Desired state: " + desired_state + "    Current state: " + current_state
            minute_count = 0
            while (minute_count < timeout_in_minutes):
                if (current_state == desired_state):
                    break
                print "Sleeping 60 seconds, iteration " + str(minute_count+1) + " of " + str(timeout_in_minutes) + ", desired state (" + desired_state+") != current state("+current_state+")"
                time.sleep(60)
                minute_count += 1
                self.refresh()
                current_state = self.power_state
                if (minute_count==timeout_in_minutes) and (current_state != desired_state):
                    raise Exception("timeout reached("+str(timeout_in_minutes)+" minutes) before desired state (" +
                                     desired_state+") reached... current state("+current_state+")")
    class SetRetirementDate(Base):
        _date_edit_field_locator = (By.CSS_SELECTOR, "input#miq_date_1")
        _retirement_warning_edit_field_locator = (By.CSS_SELECTOR, "select#retirement_warn")
        _save_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Save Changes']")
        _cancel_button_locator = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Cancel']")
        _remove_retirement_date_button_locator = (By.ID, "remove_button")

        @property
        def date_field(self):
            return self.selenium.find_element(*self._date_edit_field_locator) 

        @property
        def save_button(self):
            return self.get_element(*self._save_button_locator)

        @property
        def cancel_button(self):
            return self.get_element(*self._cancel_button_locator)

        @property
        def remove_button(self):
            return self.get_element(*self._remove_retirement_date_button_locator)

        def click_on_cancel(self):
            self._wait_for_visible_element(*self._cancel_button_locator)
            self.cancel_button.click()
            self._wait_for_results_refresh()
            return Services.VirtualMachineDetails(self.testsetup)

        def click_on_save(self):
            self._wait_for_visible_element(*self._save_button_locator)
            self.save_button.click()
            self._wait_for_results_refresh()
            return Services.VirtualMachineDetails(self.testsetup)

        def click_on_remove(self):
            self._wait_for_visible_element(*self._remove_retirement_date_button_locator)
            self.remove_button.click()
            self._wait_for_results_refresh()
            return Services.SetRetirementDate(self.testsetup)

        def fill_data(self, retirement_date, retirement_warning):
            if(retirement_date):
                self.date_field._parent.execute_script("$j('#miq_date_1').attr('value', '%s')" % retirement_date)
                self._wait_for_results_refresh() 

            if(retirement_warning):
                self.select_dropdown(retirement_warning, *self._retirement_warning_edit_field_locator)
                self._wait_for_results_refresh()       
 
    class VirtualMachineUtil(Base):
        _interval_input_field_locator = (By.CSS_SELECTOR, "select#perf_typ")
        _daily_show_edit_field_locator = (By.CSS_SELECTOR, "select#perf_days")
        _recent_show_edit_field_locator = (By.CSS_SELECTOR, "select#perf_minutes")
        _time_zone_edit_field_locator = (By.CSS_SELECTOR, "select#time_zone")
        _compare_to_edit_field_locator = (By.CSS_SELECTOR, "select#compare_to")
        _date_edit_field_locator = (By.CSS_SELECTOR, "input#miq_date_1")
        _options_frame_locator = (By.ID, "perf_options_div")

        @property
        def options_frame(self):
            return self.selenium.find_element(*self._options_frame_locator)
 
        @property
        def date_field(self):
            return self.selenium.find_element(*self._date_edit_field_locator)        

        def fill_data(self, interval,  show, time_zone, compare_to, date):
            if(interval):
                self.select_dropdown(interval, *self._interval_input_field_locator)
                self._wait_for_results_refresh()
                time.sleep(20) #issue 104 workaround
            if(date):
                self.date_field._parent.execute_script("$j('#miq_date_1').attr('value', '%s')" % date)                
                self._wait_for_results_refresh()
                time.sleep(20) #issue 104 workaround            
            if(show and interval == "Daily"):
                self.select_dropdown(show, *self._daily_show_edit_field_locator)
                self._wait_for_results_refresh()
                time.sleep(20) #issue 104 workaround
            if (show and interval == "Most Recent Hour"):
                self.select_dropdown(show, *self._recent_show_edit_field_locator)
                self._wait_for_results_refresh()
                time.sleep(20) #issue 104 workaround  
            if(time_zone):
                self.select_dropdown(time_zone, *self._time_zone_edit_field_locator)
                self._wait_for_results_refresh()
                time.sleep(20) #issue 104 workaround
            if(compare_to):
                self.select_dropdown(compare_to, *self._compare_to_edit_field_locator)
                self._wait_for_results_refresh()
                time.sleep(20) #issue 104 workaround
            self._wait_for_results_refresh()
            time.sleep(20) #issue 104 workaround

    #class EditVm(Base):
    #    _page_title = 'CloudForms Management Engine: Virtual Machines'
    #    _custom_identifier_locator = (By.ID, 'custom_1')
    #    _description_locator = (By.ID, 'description')
    #    _parent_select_location = (By.ID, 'chosen_parent')
    #    _child_vms_chosen_locator = (By.ID, 'kids_chosen')
    #    _available_vms_chosen_locator = (By.ID, 'choices_chosen')
    #
    #    # TODO: how do I know which page its going back to, All_VMs or vm_details
    #    def click_on_cancel(self):
    #        self.selenium.find_element(*self._cancel_button_locator).click()
    #        return


    #class SetOwnership(Base):
    #    pass

    #class RightSizeRecommendations(Base):
    #    pass

    #class ReconfigureVm(Base):
    #    pass

