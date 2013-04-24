from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class ZoneSettings(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _add_new_button = (By.CSS_SELECTOR, "img[alt='Add a new zone']")
    _zones_rows_selector = (By.CSS_SELECTOR, ".style3 tr > td:nth-child(2)")

    def click_on_add_new(self):
        self.selenium.find_element(*self._add_new_button).click()
        self._wait_for_results_refresh()
        return ZoneSettings.NewZone(self.testsetup)

    def click_on_zone(self, zone_name):
        zone_element = None
        for el in self.selenium.find_elements(*self._zones_rows_selector):
            if el.text.strip() == zone_name:
              zone_element = el
              break
        if not zone_element:
            raise Exception("Zone " + zone_name + " could not be found")
        zone_element.click()
        self._wait_for_results_refresh()
        return ZoneSettings.ShowZone(self.testsetup)

    class NewZone(Base):
        _maxscans_selector = (By.CSS_SELECTOR, '#max_scans')
        _submit_button =(By.CSS_SELECTOR, "img[title='Add']")

        def set_zone_info(self, name, description, proxy_server_ip):
            self._set_field('name', name)
            self._set_field('description', description)
            self._set_field('proxy_server_ip', proxy_server_ip)

        def set_windows_credentials(self, userid, password):
            self._set_field('userid', userid)
            self._set_field('password', password)
            self._set_field('verify', password)

        def set_ntp_servers(self, ntp1, ntp2, ntp3):
            self._set_field('ntp_server_1', ntp1)
            self._set_field('ntp_server_2', ntp2)
            self._set_field('ntp_server_3', ntp3)

        def set_max_scans(self, val):
            Select(self.selenium.find_element(*self._maxscans_selector)).select_by_value(val)

        def save(self):
            self._wait_for_visible_element(*self._submit_button)
            self.selenium.find_element(*self._submit_button).click()
            self._wait_for_results_refresh()
            return ZoneSettings(self.testsetup)

        def _set_field(self, name, val):
            field = self.selenium.find_element_by_name(name)
            field.clear()
            field.send_keys(val)

    class EditZone(NewZone):
        _submit_button =(By.CSS_SELECTOR, "img[alt='Save Changes']")

        def set_zone_info(self, description, proxy_server_ip):
            self._set_field('description', description)
            self._set_field('proxy_server_ip', proxy_server_ip)

    class ShowZone(Base):
        _delete_button =(By.CSS_SELECTOR, "img[alt='Delete this Zone']")
        _edit_button =(By.CSS_SELECTOR, "img[alt='Edit this Zone']")

        def click_on_edit(self):
            self.selenium.find_element(*self._edit_button).click()
            self._wait_for_results_refresh()
            return ZoneSettings.EditZone(self.testsetup)

        def click_on_delete(self):
            self.selenium.find_element(*self._delete_button).click()
            self.handle_popup()
            self._wait_for_results_refresh()
            return ZoneSettings(self.testsetup)
