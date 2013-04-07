# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By
from pages.page import Page

class Details(Page):
    def does_info_section_exist(self, section_name):
        locator = "//h2[@class='modtitle' and (.='"+section_name+"')]/.."
        try:
            return self.selenium.find_element_by_xpath(locator).is_displayed()
        except:
            return False

    def fetch_info_section_key_value(self,section_name, key):
        data = self.fetch_info_section_data(section_name)
        return data[key]

    def fetch_info_section_data(self,section_name):
        data = {}
        info_table_locator = "//h2[@class='modtitle' and (.='"+section_name+"')]/.."
        info_table = self.selenium.find_element_by_xpath(info_table_locator)
        for row in info_table.find_elements_by_css_selector("tr"):
            cells = row.find_elements_by_css_selector("td")
            data[cells[0].text] = cells[1].text
        return data

