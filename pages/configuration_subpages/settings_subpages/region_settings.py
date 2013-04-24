from pages.base import Base
from selenium.webdriver.common.by import By
from pages.configuration_subpages.settings_subpages.zone_settings import ZoneSettings

class RegionSettings(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _zones_button = (By.CSS_SELECTOR, "div[title='View Zones']")

    def click_on_zones(self):
        self.selenium.find_element(*self._zones_button).click()
        self._wait_for_results_refresh()
        return ZoneSettings(self.testsetup)
