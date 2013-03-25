# -*- coding: utf-8 -*-

import re
from pages.base import Base
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem
from time import time, sleep

class Services(Base):
    @property
    def submenus(self):
        return {"service": lambda: None,
                "catalog": lambda: None,
                "miq_request": lambda: None,
                "vm_or_template": lambda: Services.VirtualMachines,
                }

    @property
    def is_the_current_page(self):
        '''Override for top-level menu class'''
        return self.current_subpage.is_the_current_page
    
    class VirtualMachines(Base):
        _page_title = 'CloudForms Management Engine: Virtual Machines'
        
        @property
        def quadicon_region(self):
            return Quadicons(self.testsetup,Services.VirtualMachines.VirtualMachineQuadIconItem)
        
        @property
        def paginator(self):
            from pages.regions.paginator import Paginator
            return Paginator(self.testsetup)

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
        def _power_button(self):
            from pages.regions.taskbar.power import PowerButton
            return PowerButton(self.testsetup)

        def shutdown(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self._power_button.shutdown(click_cancel)
        
        def reboot(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self._power_button.reboot(click_cancel)
        
        def power_on(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self._power_button.power_on(click_cancel)
        
        def power_off(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self._power_button.power_off(click_cancel)

        def reset(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self._power_button.reset(click_cancel)

        def suspend(self,vm_names,click_cancel):
            self.quadicon_region.mark_icon_checkbox(vm_names)
            self._power_button.suspend(click_cancel)

        #def is_host_pingable(self, ip_address):
        #    pass

        #def get_host_ip_addr(self, host_quadicon_title):
        #    pass

        def get_vm_power_state(self, vm_quadicon_title):
            return self.quadicon_region.get_quadicon_by_title(vm_quadicon_title).current_state

        def does_vm_exist(self, vm_quadicon_title):
            return self.quadicon_region.does_quadicon_exist(vm_quadicon_title) 

        def wait_for_vm_state_change(self, vm_quadicon_title, desired_state, timeout_in_minutes):
            current_state = self.get_vm_power_state(vm_quadicon_title)
            print "Desired state: " + desired_state + "    Current state: " + current_state
            minute_count = 0
            while (minute_count < timeout_in_minutes):
                if (current_state == desired_state):
                    break
                print "Sleeping 60 seconds for next check, iteration " + str(minute_count+1) + " of " + str(timeout_in_minutes)
                sleep(60)
                minute_count += 1
                self.history_buttons.refresh_button.click()
                current_state = self.get_vm_power_state(vm_quadicon_title)
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
            
