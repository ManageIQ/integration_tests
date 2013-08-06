# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
def test_checkboxtree(cnf_configuration_pg):
    Assert.true(cnf_configuration_pg.is_the_current_page)
    new_role_pg = cnf_configuration_pg.click_on_access_control()\
            .click_on_roles().click_on_add_new()
    root = new_role_pg.product_features.find_node_by_name('Everything')
    root.uncheck()
    Assert.false(root.is_checked)
    # all nodes under 'Everything' should be unchecked
    Assert.false(root.find_node_by_name('Services').is_checked)
    node = root.find_node_by_name('Infrastructure')
    node.check()
    Assert.true(node.is_checked)
