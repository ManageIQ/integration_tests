# -*- coding: utf-8 -*-

import pytest
import time
from time import sleep
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAutomate:
    def test_add_namespace_component(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        ae_pg = home_pg.header.site_navigation_menu("Automate").sub_navigation_menu("Explorer").click()
        Assert.true(ae_pg.is_the_current_page)
        ae_tree = ae_pg.accordion.current_content
        ae_pg.accordion.current_content.find_node_by_name("Datastore").click()
        ae_pg = ae_pg.click_on_add_new_namespace()
        ae_pg = ae_pg.fill_namespace_info("Training", "Training")

        ae_pg.accordion.current_content.find_node_by_name("Training").click()
        ae_pg = ae_pg.click_on_add_new_namespace()
        ae_pg = ae_pg.fill_namespace_info("Student1", "Student1")

        ae_pg.accordion.current_content.find_node_by_name("Student1").click()
        ae_pg = ae_pg.click_on_add_new_class()
        ae_pg = ae_pg.fill_class_info("Methods", "Methods", "Methods")

        #ae_pg.accordion.current_content.find_node_by_name("Methods (Methods)").click()

