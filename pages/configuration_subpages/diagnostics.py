# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.tabbuttons import TabButtons
from pages.regions.accordion import Accordion
from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
from pages.configuration_subpages.diagnostics_subpages.server_diagnostics\
    import ServerDiagnostics


class Diagnostics(Base):
    _page_title = "CloudForms Management Engine: Configuration"
    _tabbutton_region = (By.CSS_SELECTOR, "div#ops_tabs > ul > li")

    @property
    def tabbutton_region(self):
        return TabButtons(self.testsetup, locator_override=self._tabbutton_region)

    @property
    def accordion(self):
        return Accordion(self.testsetup, LegacyTreeAccordionItem)

    def click_on_current_server_tree_node(self):
        self.accordion.current_content.find_node_by_regexp(r'\AServer:.*current').click()
        self._wait_for_results_refresh()
        return ServerDiagnostics(self.testsetup)
