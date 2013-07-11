'''
Created on Jun 7, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
import pytest
from unittestzero import Assert

@pytest.fixture(params=[('title', 'Add this Infrastructure Provider'),
        ('alt', 'Add this Infrastructure Provider')])
def attribute_and_value(request):
    '''Returns a tuple containing items to test'''
    return request.param

@pytest.fixture
def provider_add_pg(infra_providers_pg):
    '''Navigate to Infrastructure -> Providers -> Add'''
    return infra_providers_pg.click_on_add_new_provider()


class TestManagementSystemsPages:
    @pytest.mark.nondestructive
    class TestManagementSystemsAddPage:
        def test_that_checks_add_button_attribute(
                self,
                provider_add_pg,
                attribute_and_value):
            attr = attribute_and_value[0]
            expected_value = attribute_and_value[1]

            add_attr = provider_add_pg.add_button.get_attribute(attr)
            Assert.equal(add_attr, expected_value,
                    "Could not verify %s" % expected_value)
