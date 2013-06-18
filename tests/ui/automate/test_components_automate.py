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
        ae_pg = ae_pg.fill_namespace_info("ATraining", "ATraining")

        ae_pg.accordion.current_content.find_node_by_name("ATraining").click()
        ae_pg = ae_pg.click_on_add_new_namespace()
        ae_pg = ae_pg.fill_namespace_info("AStudent", "AStudent")

        ae_pg.accordion.current_content.find_node_by_name("AStudent").click()
        ae_pg = ae_pg.click_on_add_new_class()
        ae_pg = ae_pg.fill_class_info("ATestMethods", "ATestMethods", "ATestMethods")

        ae_pg.accordion.current_content.find_node_by_name("ATestMethods (ATestMethods)").click()

        ae_pg.accordion.current_content.find_node_by_name("Datastore").click()
        ae_pg.click_on_namespace_item("ATraining", 0)
        ae_pg.click_on_remove_selected_namespaces()


