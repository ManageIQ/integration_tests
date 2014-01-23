# -*- coding: utf-8 -*-
# pylint: disable=R0904
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class Timelines(Base):
    _no_event_locator = (By.CSS_SELECTOR, "li#message")
    _unexpected_error_locator = (By.CSS_SELECTOR, "h1")
    _options_frame_locator = (By.ID, "tl_options_div")
    _rhev_vm_event_locator = (By.XPATH, '//img[@src="/images/icons/timeline/vm_event.png"]')
    _vsphere_vm_event_locator = (By.XPATH, '//img[@src="/images/icons/timeline/vm_power_off.png"]')

    @property
    def is_no_events_found(self):
        try:
            return self.get_element(*self._no_event_locator).text == \
                "No events available for this timeline"
        except (TimeoutException):
            return False

    @property
    def is_unexpected_error_found(self):
        try:
            return self.get_element(*self._unexpected_error_locator).text == \
                "Unexpected error encountered"
        except (TimeoutException):
            return False

    def vm_event_found(self, name):
        try:
            return self.get_element(By.XPATH, "//div[@class='timeline-band']//span[.='%s']" % name)
        except (TimeoutException):
            return False

    @property
    def rhev_vm_event_img_found(self):
        try:
            return self.get_element(*self._rhev_vm_event_locator)
        except (TimeoutException):
            return False

    @property
    def vsphere_vm_event_img_found(self):
        try:
            return self.get_element(*self._vsphere_vm_event_locator)
        except (TimeoutException):
            return False

    @property
    def is_options_frame_found(self):
        try:
            return self.get_element(*self._options_frame_locator).text == \
                "Timelines"
        except (TimeoutException):
            return False
