#!/usr/bin/env python
from selenium.webdriver.common.by import By

from base import Base

class DashboardPage(Base):
    _page_title = "CloudForms Management Engine: Dashboard"
    _reset_widgets_button_locator = (By.CSS_SELECTOR,
        'div.dhx_toolbar_btn[title="Reset Dashboard Widgets to the defaults"] img')

    @property
    def reset_widgets_button(self):
        return self.selenium.find_element(*self._reset_widgets_button_locator)

    def click_on_reset_widgets(self, cancel=False):
        self.reset_widgets_button.click()
        self.handle_popup(cancel)

