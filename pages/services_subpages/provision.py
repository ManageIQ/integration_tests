'''Created on May 1, 2013

@author: bcrochet
'''
from pages.page import Page
from pages.regions.list import ListRegion, ListItem
from pages.regions.tabbuttonitem import TabButtonItem
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class ProvisionFormButtonMixin(object):
    '''Mixin for shared buttons on the Provision wizard'''
    # BPC: This selector is used to just select the current set of buttons that
    # are visible. If tests are needed to determine *which* set of buttons is
    # visible, a different set of selectors and properties should be created
    _template_form_buttons_locator = (
            By.CSS_SELECTOR,
            "div#form_buttons_div > table > tbody > tr > td > div")
    _template_continue_button_locator = (
            By.CSS_SELECTOR,
            "li img[alt='Submit']")
    _template_cancel_button_locator = (
            By.CSS_SELECTOR,
            "li img[alt='Cancel']")

    # NOTE: Not sure if this is the best way to go about this. Should the test
    # itself worry about what set of buttons is enabled/disabled? I certainly
    # think both need to be exposed. It may be that since one can only operate
    # on the "visible" buttons, it may be better to just expose the set that
    # are visible, as below.
    @property
    def _form_buttons(self):
        '''Represents the set of form buttons.'''
        # TODO: Find a better way to do this. Preferably in the selector itself
        button_divs = self.selenium.find_elements(
                *self._template_form_buttons_locator)
        for div in button_divs:
            if "block" in div.value_of_css_property('display'):
                return div.find_element_by_css_selector("ul#form_buttons")
        return None

    @property
    def continue_button(self):
        '''The continue button. Will select the "visible" one'''
        return self._form_buttons.find_element(
                *self._template_continue_button_locator)

    @property
    def cancel_button(self):
        '''The cancel button. Will select the "visible" one'''
        return self._form_buttons.find_element(
                *self._template_cancel_button_locator)

class ProvisionTabButtonItem(TabButtonItem):
    '''Specialization of TabButtonItem'''
    from pages.services_subpages.provision_subpages.provision_request import ProvisionRequest
    from pages.services_subpages.provision_subpages.provision_catalog import ProvisionCatalog
    from pages.services_subpages.provision_subpages.provision_purpose import ProvisionPurpose
    from pages.services_subpages.provision_subpages.provision_environment import ProvisionEnvironment
    from pages.services_subpages.provision_subpages.provision_hardware import ProvisionHardware
    from pages.services_subpages.provision_subpages.provision_network import ProvisionNetwork
    from pages.services_subpages.provision_subpages.provision_customize import ProvisionCustomize
    from pages.services_subpages.provision_subpages.provision_schedule import ProvisionSchedule

    _item_page = {
                "Request": ProvisionRequest,
                "Purpose": ProvisionPurpose,
                "Catalog": ProvisionCatalog,
                "Environment": ProvisionEnvironment,
                "Hardware": ProvisionHardware,
                "Network": ProvisionNetwork,
                "Customize": ProvisionCustomize,
                "Schedule": ProvisionSchedule
            }

class ProvisionSelectionChain():
    _provision_vms_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Request to Provision VMs']")

    @property
    def center_buttons(self):
        from pages.regions.taskbar.center import CenterButtons
        return CenterButtons(self.testsetup)

    def click_on_lifecycle(self):
        provision_vms_button = self.get_element(*self._provision_vms_button_locator)

        ActionChains(self.selenium).click(self.center_buttons.lifecycle_button).click(provision_vms_button).perform()
        from pages.services_subpages.provision import ProvisionStart
        return ProvisionStart(self.testsetup)

class ProvisionStart(Page, ProvisionFormButtonMixin):
    '''Page representing the start of the Provision VMs "wizard"'''
    _page_title = "CloudForms Management Engine: Virtual Machines"
    _template_list_locator = (
            By.CSS_SELECTOR,
            "div#pre_prov_div > fieldset > table > tbody")

    def click_on_continue(self):
        '''Click on the continue button. Returns the next page in the provision
        wizard. Provision
        '''
        self.continue_button.click()
        self._wait_for_results_refresh()
        return Provision(self.testsetup)

    def click_on_cancel(self):
        '''Click on the cancel button. Returns the
        Services.VirtualMachines page.
        '''
        from pages.services import Services
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return Services.VirtualMachines(self.testsetup)

    @property
    def template_list(self):
        '''Returns the template list region'''
        return ListRegion(
                self.testsetup,
                self.get_element(*self._template_list_locator),
                self.TemplateItem)

    def click_on_template_item(self, item_name):
        '''Select template item by name'''
        template_items = self.template_list.items
        selected_item = template_items[[item for item in range(len(template_items)) if template_items[item].name == item_name][0]]
        selected_item.click()
        self._wait_for_results_refresh()
        return self.TemplateItem(selected_item)

    class TemplateItem(ListItem):
        '''Represents an item in the template list'''
        _columns = ["name", "operating_system", "platform", "cpus", "memory",
                "disk_size", "management_system", "snapshots"]

        @property
        def name(self):
            '''Template name'''
            return self._item_data[0].text

        @property
        def operating_system(self):
            '''Template operating system'''
            return self._item_data[1].text

        @property
        def platform(self):
            '''Template platform'''
            return self._item_data[2].text

        @property
        def cpus(self):
            '''Template CPU count'''
            return self._item_data[3].text

        @property
        def memory(self):
            '''Template memory'''
            return self._item_data[4].text

        @property
        def disk_size(self):
            '''Template disk size'''
            return self._item_data[5].text

        @property
        def management_system(self):
            '''Template management system'''
            return self._item_data[6].text

        @property
        def snapshots(self):
            '''Template snapshot count'''
            return self._item_data[7].text

class Provision(Page, ProvisionFormButtonMixin):
    '''Represents the final page in the Provision VM wizard'''
    _page_title = "CloudForms Management Engine: Virtual Machines"
    _tab_button_locator = (By.CSS_SELECTOR, "div#prov_tabs > ul > li")

    @property
    def tabbutton_region(self):
        '''Return the tab button region'''
        from pages.regions.tabbuttons import TabButtons
        return TabButtons(self.testsetup,
                self._tab_button_locator,
                ProvisionTabButtonItem)

    def click_on_cancel(self):
        '''Click on cancel button. Return to Services.VirtualMachines'''
        self.cancel_button.click()
        self._wait_for_results_refresh()
        from pages.services import Services
        return Services.VirtualMachines(self.testsetup)

    def click_on_submit(self):
        ''' Click on the submit button. Go to Requests page'''
        self.continue_button.click()
        self._wait_for_results_refresh()
        from pages.services import Services
        return Services.Requests(self.testsetup)
