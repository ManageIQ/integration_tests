import pytest
from unittestzero import Assert
from selenium.webdriver.common.by import By

class TestSearch:        
        
    @pytest.mark.nondestructive
    def test_search_zero_results(self, mozwebqa, home_page_logged_in):
        vm_pg = home_page_logged_in.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Virtual Machines").click()
        vm_pg.search.search_by_name('not_found')
        body = vm_pg.selenium.find_element_by_tag_name("body");
        Assert.true("Names with \"not_found\"" in body.text)
        Assert.true("No Records Found" in body.text)
