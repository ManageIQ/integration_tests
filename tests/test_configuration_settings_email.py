#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestEmailServer:
    def test_outgoing_smtp_email_server(self, cnf_configuration_pg):
        server_pg = cnf_configuration_pg.click_on_settings()\
            .click_on_current_server_tree_node().click_on_server_tab()
        email_data = dict(
            host='test_localhost',
            port='2525',
            domain='testdomain.test',
            tls='True',
            ssl_mode='Peer',
            authentication='plain',
            user_name='test_username',
            password='test_password',
            from_email='test_fromemail@testing.test',
            test_email='test_testemail@letsgoto.pub')
        server_pg.setup_outgoing_smtp_email_server(**email_data)
        server_pg.click_on_reset()
        flash_message = "All changes have been reset"
        Assert.equal(server_pg.flash.message, flash_message, server_pg.flash.message)
