# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
from pages.regions.tree import LegacyTree

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
def test_automate_components(automate_explorer_pg):
    '''Tests components for Automate Explorer Tree'''
    ae_pg = automate_explorer_pg
    Assert.true(ae_pg.is_the_current_page)

    nodes = [
        "Datastore",
        "Alert",
        "Automation",
        "EVMApplications",
        "Factory",
        "Integration",
        "System",
        "Datastore"
        ]
    for node in nodes:
        ae_pg.accordion.current_content.find_node_by_name(node).click()

    ae_pg.click_on_namespace_access_node("Sample")
    ae_tree = ae_pg.accordion.current_content
    Assert.equal(type(ae_tree), LegacyTree)
