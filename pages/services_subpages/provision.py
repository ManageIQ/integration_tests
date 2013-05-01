'''Created on May 1, 2013

@author: bcrochet
'''
from pages.page import Page
from selenium.webdriver.common.by import By

class ProvisionStart(Page):
    '''Page representing the start of the Provision VMs "wizard"'''
    _page_title = "CloudForms Management Engine: Virtual Machines"
    _template_list_locator = (
            By.CSS_SELECTOR,
            "div#pre_prov_div > fieldset > table > tbody")
    _template_continue_button_locator = (
            By.CSS_SELECTOR,
            "li img[title='Continue']")
    _template_cancel_button_locator = (
            By.CSS_SELECTOR,
            "li img[title='Cancel']")

    # BPC: This selector is used to just select the current set of buttons that
    # are visible. If tests are needed to determine *which* set of buttons is
    # visible, a different set of selectors and properties should be created
    _template_form_buttons_locator = (
            By.CSS_SELECTOR,
            "div#form_buttons_div > table > tbody > tr > td > div")


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

    def click_on_continue(self):
        '''Click on the continue button. Returns the next page in the provision
        wizard. Provision
        '''
        self.continue_button.click()
        return Provision(self.testsetup)

    def click_on_cancel(self):
        '''Click on the cancel button. Returns the
        Services.VirtualMachines page.
        '''
        from pages.services import Services
        self.cancel_button.click()
        return Services.VirtualMachines(self.testsetup)

    @property
    def template_region(self):
        '''Returns the template list region'''
        return self.TemplateRegion(
                self.testsetup,
                self.selenium.find_element(*self._template_list_locator))

    class TemplateRegion(Page):
        '''Represents the template list region'''
        _template_items_locator = (By.CSS_SELECTOR, "tr")

        @property
        def templates(self):
            '''Returns a list of TemplateItems'''
            return [self.TemplateItem(self.testsetup, web_element)
                    for web_element in self._root_element.find_elements(
                            *self._template_items_locator)]

        class TemplateItem(Page):
            '''Represents an item in the template list'''
            _template_data_locator = (By.CSS_SELECTOR, "td")

            def click(self):
                '''Click on the item, which will select it in the list'''
                self._root_element.click()

            @property
            def _template_data(self):
                return [web_element.text
                        for web_element in self._root_element.find_elements(
                                *self._template_data_locator)]

            @property
            def name(self):
                '''Template name'''
                return self._template_data[0]

            @property
            def operating_system(self):
                '''Template operating system'''
                return self._template_data[1]

            @property
            def platform(self):
                '''Template platform'''
                return self._template_data[2]

            @property
            def cpus(self):
                '''Template CPU count'''
                return self._template_data[3]

            @property
            def memory(self):
                '''Template memory'''
                return self._template_data[4]

            @property
            def disk_size(self):
                '''Template disk size'''
                return self._template_data[5]

            @property
            def management_system(self):
                '''Template management system'''
                return self._template_data[6]

            @property
            def snapshots(self):
                '''Template snapshot count'''
                return self._template_data[7]

class Provision(Page):
    _page_title = "CloudForms Management Engine: Virtual Machines"
