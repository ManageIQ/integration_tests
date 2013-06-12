'''
Created on Jun 7, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.fixture(params=[('title', 'Add this Management System'),
        ('alt', 'Add this Management System')])
def attribute_and_value(request):
    return request.param

@pytest.fixture
def mgmtsys_add_pg(mgmtsys_page):
    return mgmtsys_page.click_on_add_new_management_system()


class TestManagementSystemsPages:
    @pytest.mark.nondestructive
    class TestManagementSystemsAddPage:
        def test_that_checks_add_button_attribute(self, mgmtsys_add_pg, attribute_and_value):
            attr = attribute_and_value[0]
            expected_value = attribute_and_value[1]

            add_attr = mgmtsys_add_pg.add_button.get_attribute(attr)
            Assert.equal(add_attr, expected_value, "Could not verify %s" % expected_value)
