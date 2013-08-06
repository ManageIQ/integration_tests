# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.fixture
def namespace(random_string):
    '''Returns random name for namespace'''
    return '%s_namespace' % random_string

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
def test_automate_components(automate_explorer_pg, namespace):
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
    ae_pg = ae_pg.click_on_add_new_namespace()
    ae_pg = ae_pg.fill_namespace_info(namespace, namespace)

    # teardown - remove parent namespace
    ae_namespace_pg = ae_pg.click_on_namespace_access_node("Datastore")
    ae_namespace_pg.click_on_namespace_item(namespace)
    ae_namespace_pg.click_on_remove_selected_namespaces()

