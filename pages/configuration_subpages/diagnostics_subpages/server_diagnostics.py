from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.accordion import Accordion
from pages.regions.tabbuttons import TabButtons
from pages.regions.treeaccordionitem import LegacyTreeAccordionItem


class ServerDiagnostics(Base):
    _page_title = "CloudForms Management Engine: Configuration"
    _tabbutton_region = (By.CSS_SELECTOR, "div#ops_tabs > ul > li")

    @property
    def tabbutton_region(self):
        return TabButtons(self.testsetup, locator_override=self._tabbutton_region)

    @property
    def accordion(self):
        return Accordion(self.testsetup, LegacyTreeAccordionItem)

    # Tabs
    def click_on_workers_tab(self):
        from pages.configuration_subpages.diagnostics_subpages\
            .server_diagnostics_subpages.worker_diagnostics_tab\
            import WorkerDiagnosticsTab
        self.tabbutton_region.tabbutton_by_name('Workers').click()
        self._wait_for_results_refresh()
        return WorkerDiagnosticsTab(self.testsetup)

    def click_on_collect_logs_tab(self):
        from pages.configuration_subpages.diagnostics_subpages\
            .server_diagnostics_subpages.collect_logs_tab\
            import CollectLogsTab
        self.tabbutton_region.tabbutton_by_name('Collect Logs').click()
        self._wait_for_results_refresh()
        return CollectLogsTab(self.testsetup)
