#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert


@pytest.mark.usefixtures("maximized")
@pytest.mark.nondestructive
class TestSettings:
    def test_configure_aws_iam(self, cnf_configuration_pg):
        _aws_iam_settings = {"access_key": "TESTACCESSKEY",
                             "secret_key": "TESTSECRETKEY"
                             }
        auth_pg = cnf_configuration_pg.click_on_settings()\
                .click_on_current_server_tree_node()\
                .click_on_authentication_tab()
        Assert.true(auth_pg.is_the_current_page)
        auth_pg.aws_iam_fill_data(**_aws_iam_settings)
        auth_pg = auth_pg.reset()
        Assert.equal(auth_pg.flash.message, "All changes have been reset")
