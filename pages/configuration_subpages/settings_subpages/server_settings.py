from pages.base import Base
from selenium.webdriver.common.by import By

class ServerSettings(Base):
    _page_title = 'CloudForms Management Engine: Configuration'

    @property
    def accordion(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import TreeAccordionItem
        return Accordion(self.testsetup,TreeAccordionItem)

    @property
    def tabbutton_region(self):
        from pages.regions.tabbuttons import TabButtons
        return TabButtons(self.testsetup, locator_override = (By.CSS_SELECTOR, "div#ops_tabs > ul > li"))

    def click_on_server_tab(self):
        from pages.configuration_subpages.settings_subpages.server_settings_subpages.server_settings_tab import ServerSettingsTab
        self.tabbutton_region.tabbutton_by_name('Server').click()
        self._wait_for_results_refresh()
        return ServerSettingsTab(self.testsetup)
