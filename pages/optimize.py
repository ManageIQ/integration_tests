from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from pages.base import Base
from pages.regions.details import Details
from pages.regions.tabbuttonitem import TabButtonItem
from pages.regions.treeaccordionitem import TreeAccordionItem
from pages.regions.tree import Tree

class UtilizationDetails(Details):
    """Override Details base because of silly selectors

    See BZ#(https://bugzilla.redhat.com/show_bug.cgi?id=975189)

    """

    _details_section_locator = (By.CSS_SELECTOR, "fieldset")

    @property
    def sections(self):
        return [UtilizationDetails.UtilizationDetailsSection(self.testsetup, web_element)
                for web_element in self._root_element.find_elements(*self._details_section_locator)]

    class UtilizationDetailsSection(Details.DetailsSection):
        _details_section_name_locator = (By.CSS_SELECTOR, "p.legend")
        #_details_section_data_locator = (By.CSS_SELECTOR, "tr")

        @property
        def items(self):
            return [UtilizationDetails.UtilizationDetailsItem(self.testsetup, web_element)
                    for web_element in self._root_element.find_elements(*self._details_section_data_locator)]

    class UtilizationDetailsItem(Details.DetailsSection.DetailsItem):
            _details_section_data_key_locator = (By.CSS_SELECTOR, "td")
            _details_section_data_value_locator = (By.CSS_SELECTOR, "td:nth-child(2)")

class Optimize(Base):
    @property
    def submenus(self):
        return{"utilization" : Optimize.Utilization}

    class Utilization(Base):
        _page_title = 'CloudForms Management Engine: Optimize'

        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
            return Accordion(self.testsetup, LegacyTreeAccordionItem)

        def click_on_node(self, node_name):
            node_pg = self.accordion.accordion_by_name("Utilization").click()
            tree = self.accordion.current_content
            node_pg = tree.find_node_by_name(node_name).click()
            self._wait_for_results_refresh()
            return Optimize.Node(self.testsetup)        

    class Node(Utilization, Base):
        _page_title = 'CloudForms Management Engine: Optimize'
 
        @property
        def tab_buttons(self):
            from pages.regions.tabbuttons import TabButtons
            return TabButtons(self.testsetup, locator_override = (By.CSS_SELECTOR, "div#utilization_tabs > ul > li"))
 
        def _click_on_tab_button(self, name, cls):
            btn = self.tab_buttons.tabbutton_by_name(name)
            self._wait_for_results_refresh()
            btn.click()
            self._wait_for_results_refresh()
            return cls(self.testsetup)
 
        def click_on_summary(self):
            return self._click_on_tab_button("Summary", Optimize.Summary)
 
        def click_on_details(self):
            return self._click_on_tab_button("Details", Optimize.Details)
 
        def click_on_report(self):
            return self._click_on_tab_button("Report", Optimize.Report)


    class Summary(Node, Base):
        _page_title = 'CloudForms Management Engine: Optimize'
        _trends_edit_field_locator = (By.CSS_SELECTOR, "select#summ_days")
        _classification_edit_field_locator = (By.CSS_SELECTOR, "select#summ_tag")
        _time_zone_edit_field_locator = (By.CSS_SELECTOR, "select#summ_tz")
        _details_locator = (By.CSS_SELECTOR, "div#main_div")
        _date_edit_field_locator = (By.CSS_SELECTOR, "input#miq_date_1")

        @property
        def date_field(self):
            return self.selenium.find_element(*self._date_edit_field_locator)

        @property 
        def details(self):
            root_element = self.selenium.find_element(*self._details_locator)
            return UtilizationDetails(self.testsetup, root_element)

        def fill_data(self, trends, classification, time_zone, date):
            if(trends):
                self.select_dropdown(trends, *self._trends_edit_field_locator)
                self._wait_for_results_refresh()
            if(classification):
                self.select_dropdown(classification, *self._classification_edit_field_locator)
                self._wait_for_results_refresh()
            if(time_zone):
                self.select_dropdown(time_zone, *self._time_zone_edit_field_locator)
                self._wait_for_results_refresh()
            if(date):
                self.date_field._parent.execute_script("$j('#miq_date_1').attr('value', '%s')" % date)
                self._wait_for_results_refresh()
            self._wait_for_results_refresh()

    class Details(Node, Base):
        _page_title = 'CloudForms Management Engine: Optimize'
        _trends_edit_field_locator = (By.CSS_SELECTOR, "select#details_days")
        _classification_edit_field_locator = (By.CSS_SELECTOR, "select#details_tag")
        _time_zone_edit_field_locator = (By.CSS_SELECTOR, "select#details_tz")
        _details_locator = (By.CSS_SELECTOR, "div#main_div")

        @property
        def details(self):
            root_element = self.selenium.find_element(*self._details_locator)
            return UtilizationDetails(self.testsetup, root_element)

        def fill_data(self, trends, classification, time_zone):
            if(trends):
                self.select_dropdown(trends, *self._trends_edit_field_locator)
                self._wait_for_results_refresh()
            if(classification):
                self.select_dropdown(classification, *self._classification_edit_field_locator)
                self._wait_for_results_refresh()
            if(time_zone):
                self.select_dropdown(time_zone, *self._time_zone_edit_field_locator)
                self._wait_for_results_refresh()
            self._wait_for_results_refresh()

    class Report(Node, Base):
        _page_title = 'CloudForms Management Engine: Optimize'
        _trends_edit_field_locator = (By.CSS_SELECTOR, "select#report_days")
        _classification_edit_field_locator = (By.CSS_SELECTOR, "select#report_tag")
        _time_zone_edit_field_locator = (By.CSS_SELECTOR, "select#report_tz")
        _details_locator = (By.CSS_SELECTOR, "div#main_div")
        _date_edit_field_locator = (By.CSS_SELECTOR, "input#miq_date_2")

        @property
        def date_field(self):
            return self.selenium.find_element(*self._date_edit_field_locator)

        @property
        def details(self):
            root_element = self.selenium.find_element(*self._details_locator)
            return UtilizationDetails(self.testsetup, root_element)


        def fill_data(self, trends, classification, time_zone, date):
            if(trends):
                self.select_dropdown(trends, *self._trends_edit_field_locator)
                self._wait_for_results_refresh()
            if(classification):
                self.select_dropdown(classification, *self._classification_edit_field_locator)
                self._wait_for_results_refresh()
            if(time_zone):
                self.select_dropdown(time_zone, *self._time_zone_edit_field_locator)
                self._wait_for_results_refresh()
            if(date):
                self.date_field._parent.execute_script("$j('#miq_date_2').attr('value', '%s')" % date)
                self._wait_for_results_refresh()
            self._wait_for_results_refresh()
                            
