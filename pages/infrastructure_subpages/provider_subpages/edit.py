from selenium.webdriver.common.by import By

from pages.infrastructure_subpages.provider_subpages.add import ProvidersAdd
from pages.infrastructure_subpages.provider_subpages.detail import ProvidersDetail


class ProvidersEdit(ProvidersAdd):
    """Provider Edit Form

    Almost identical to the provider add form, except:

    - You can't change the provider type (so don't try...)
    - 'Save' and 'Reset' buttons instead of 'Add'
    - VNC port field elements appear
    """
    _reset_button_locator = (
        By.CSS_SELECTOR,
        "div#buttons_on > ul#form_buttons > li > img[title='Reset Changes']")
    _save_button_locator = (
        By.CSS_SELECTOR,
        "div#buttons_on > ul#form_buttons > li > img[title='Save Changes']")
    _host_default_vnc_port_start_edit_field_locator = (By.ID, "host_default_vnc_port_start")
    _host_default_vnc_port_end_edit_field_locator = (By.ID, "host_default_vnc_port_end")

    def select_provider_type(self, provider_type):
        # Can't do this on an edit page
        pass

    def edit_provider(self, provider):
        self._fill_provider(provider)
        if "host_vnc_port" in provider:
            self.fill_field_element(provider['host_vnc_port']['start'],
                self.host_default_vnc_port_start)
            self.fill_field_element(provider['host_vnc_port']['end'],
                self.host_default_vnc_port_end)
        return self.click_on_save()

    @property
    def host_default_vnc_port_start(self):
        '''Infrastructure Provider VNC port start'''
        return self.get_element(*self._host_default_vnc_port_start_edit_field_locator)

    @property
    def host_default_vnc_port_end(self):
        '''Infrastructure Provider VNC port end'''
        return self.get_element(*self._host_default_vnc_port_end_edit_field_locator)

    @property
    def save_button(self):
        '''Save button'''
        return self.get_element(*self._save_button_locator)

    # Point add_button over to save_button to ensure superclass methods work
    add_button = save_button

    @property
    def reset_button(self):
        '''Reset button'''
        return self.get_element(*self._reset_button_locator)

    def click_on_save(self):
        '''Click on save button'''
        self.save_button.click()
        self._wait_for_results_refresh()
        return ProvidersDetail(self.testsetup)

    def click_on_reset(self):
        '''Click on reset button'''
        self.reset_button.click()
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.providers import Providers
        return Providers(self.testsetup)
