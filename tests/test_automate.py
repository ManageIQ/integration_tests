# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
def test_automate_components(automate_explorer_pg):
    '''Tests components for Automate Explorer Tree'''
    ae_pg = automate_explorer_pg
    ae_tree = ae_pg.accordion.current_content
    Assert.true(ae_pg.is_the_current_page)

    nodes = [
        "Datastore",
        "Alert",
        "Automation",
        "EVMApplications",
        "Factory",
        "Integration"
        ]
    for node in nodes:
        ae_pg.accordion.current_content.find_node_by_name(node).click()

    ae_pg.click_on_namespace_access_node("Sample")
    Assert.equal(ae_tree.children[5].children[0].name, "Methods")
    ae_pg.accordion.current_content.find_node_by_name("System").click()
    ae_pg.accordion.current_content.find_node_by_name("Datastore").click()
