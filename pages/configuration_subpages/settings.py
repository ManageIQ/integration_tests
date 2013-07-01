'''
@author: unknown
'''
from pages.base import Base
from pages.configuration_subpages.settings_subpages.server_settings\
        import ServerSettings
from pages.configuration_subpages.settings_subpages.region_settings\
        import RegionSettings
from pages.configuration_subpages.settings_subpages.zone_settings\
        import ZoneSettings

class Settings(Base):
    _page_title = 'CloudForms Management Engine: Configuration'

    @property
    def accordion(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
        return Accordion(self.testsetup, LegacyTreeAccordionItem)

    # select a server in left accordion tree panel
    def click_on_current_server_tree_node(self):
        self.accordion.current_content.find_node_by_regexp(
                r'\AServer:.*current').click()
        self._wait_for_results_refresh()
        return ServerSettings(self.testsetup)

    # select a server in left accordion tree panel
    def click_on_first_region(self):
        self.accordion.current_content.find_node_by_regexp(
                r'\ARegion:').click()
        self._wait_for_results_refresh()
        return RegionSettings(self.testsetup)

    def click_on_zones(self):
        self.accordion.current_content.find_node_by_regexp(
                r'\AZones').click()
        self._wait_for_results_refresh()
        return ZoneSettings(self.testsetup)