# -*- coding: utf-8 -*-

import re
from pages.base import Base
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.paginator import PaginatorMixin
from time import time, sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

class Services(Base):
    @property
    def submenus(self):
        return {"services"       : None,
                "catalogs"       : None,
                "miq_request_vm" : None,
                "vmx"            : Services.VirtualMachines,
                }

    @property
    def is_the_current_page(self):
        '''Override for top-level menu class'''
        return self.current_subpage.is_the_current_page
    
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

        def shutdown(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.power_button.shutdown(click_cancel)
        
        def restart(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.power_button.restart(click_cancel)
        
        def power_on(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.power_button.power_on(click_cancel)
        
        def power_off(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.power_button.power_off(click_cancel)

        def reset(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.power_button.reset(click_cancel)

        def suspend(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.power_button.suspend(click_cancel)

        def smart_state_scan(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.config_button.perform_smart_state_analysis(click_cancel)

        def refresh_relationships(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.config_button.refresh_relationships(click_cancel)

        def extract_running_processes(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.config_button.extract_running_processes(click_cancel)

        #def edit_vm(self,vm_name,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox([vm_name])
        #    return Services.EditVm(self.testsetup, vm_name)

        #def set_ownership(self,vm_names,click_cancel):
        #    self.quadicon_region.mark_icon_checkbox(vm_names)
        #    return Services.SetOwnership(self.testsetup, vm_names)

        def remove_from_vmdb(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self.config_button.remove_from_vmdb(click_cancel)

        def click_on_provision_vms(self):
            provision_vms_button = self.get_element(*self._provision_vms_button_locator)
            ActionChains(self.selenium).click(self.center_buttons.lifecycle_button).click(provision_vms_button).perform()
            from pages.services_subpages.provision import ProvisionStart
            return ProvisionStart(self.testsetup)

        def find_vm_page(self, vm_name, vm_type, mark_checkbox, load_details = False):
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
                print "Sleeping 60 seconds for next check, iteration " + str(minute_count+1) + " of " + str(timeout_in_minutes)
                sleep(60)
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

        def wait_for_vm_state_change(self, desired_state, timeout_in_minutes):
            current_state = self.power_state
            print "Desired state: " + desired_state + "    Current state: " + current_state
            minute_count = 0
            while (minute_count < timeout_in_minutes):
                if (current_state == desired_state):
                    break
                print "Sleeping 60 seconds for next check, iteration " + str(minute_count+1) + " of " + str(timeout_in_minutes)
                sleep(60)
                minute_count += 1
                self.refresh()
                current_state = self.power_state
                if (minute_count==timeout_in_minutes) and (current_state != desired_state):
                    raise Exception("timeout reached("+str(timeout_in_minutes)+" minutes) before desired state (" +
                                     desired_state+") reached... current state("+current_state+")")


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

