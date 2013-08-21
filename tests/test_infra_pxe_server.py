#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

NAME = "rhel_pxe_server"

@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("maximized")
class TestPXEServer:
    def test_pxe_server(self, infra_pxe_pg):
        Assert.true(infra_pxe_pg.is_the_current_page)

        infra_pxe_pg.accordion_region.accordion_by_name("PXE Servers").click()
        infra_pxe_pg.accordion_region.current_content.click()

        infra_pxe_pg.center_buttons.configuration_button.click()
        add_pg = infra_pxe_pg.click_on_add_pxe_server()
        selected_pg = add_pg.select_depot_type("Network File System")
        selected_pg.new_pxe_server_fill_data()
        cancelled_pg = selected_pg.click_on_cancel()
        cancel_message = 'Add of new PXE Server was cancelled by the user'
        Assert.equal(cancelled_pg.flash.message, cancel_message, cancelled_pg.flash.message)

