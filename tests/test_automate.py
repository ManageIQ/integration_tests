# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAutomateTree:
    def test_automate_components(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        ae_pg = home_pg.header.site_navigation_menu("Automate").sub_navigation_menu("Explorer").click()
        Assert.true(ae_pg.is_the_current_page)
        ae_tree = ae_pg.accordion.current_content
        ae_pg.accordion.current_content.find_node_by_name("Datastore").click()
        ae_pg.accordion.current_content.find_node_by_name("Alert").click()
        ae_pg.accordion.current_content.find_node_by_name("Automation").click()
        ae_pg.accordion.current_content.find_node_by_name("EVMApplications").click()
        ae_pg.accordion.current_content.find_node_by_name("Factory").click()
        ae_pg.accordion.current_content.find_node_by_name("Integration").click()

        ae_pg.accordion.current_content.find_node_by_name("Sample").click()
        ae_tree = ae_pg.accordion.current_content
        Assert.true(ae_tree.children[5].children[0].name == "Methods")

        ae_pg.accordion.current_content.find_node_by_name("System").click()

        ae_pg.accordion.current_content.find_node_by_name("Datastore").click()
        ae_pg = ae_pg.click_on_add_new_namespace()
        ae_pg = ae_pg.fill_namespace_info("Test", "PageTest")
