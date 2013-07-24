# -*- coding: utf-8 -*-
# pylint: disable=R0904

from pages.base import Base
from pages.regions.paginator import PaginatorMixin
from selenium.common.exceptions import NoSuchElementException

class VmCommonComponents(Base, PaginatorMixin):

    _page_title = 'CloudForms Management Engine: Virtual Machines'

    @property
    def accordion(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import TreeAccordionItem
        return Accordion(self.testsetup, TreeAccordionItem)

    @property
    def history_buttons(self):
        from pages.regions.taskbar.history import HistoryButtons
        return HistoryButtons(self.testsetup)

    @property
    def view_buttons(self):
        from pages.regions.taskbar.view import ViewButtons
        return ViewButtons(self.testsetup)

    @property
    def center_buttons(self):
        from pages.regions.taskbar.center import CenterButtons
        return CenterButtons(self.testsetup)

    def refresh(self):
        '''Refresh the page by clicking the refresh button that is 
            part of the history button region.

        Note:
            Contains try/except because of page differences depending on how the page
            is loaded... mgmt_system all_vms click through (which does not have the 
            refresh button) versus services tab > VMs

            When the refresh button is not found, a browser refresh is performed.
        '''
        try:
            self.history_buttons.refresh_button.click()
            self._wait_for_results_refresh()
        except NoSuchElementException:
            self.selenium.refresh()

    @property
    def power_button(self):
        from pages.regions.taskbar.power import PowerButton
        return PowerButton(self.testsetup)

    @property
    def config_button(self):
        from pages.regions.taskbar.vm_configuration import ConfigButton
        return ConfigButton(self.testsetup)

