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

        time.sleep(1)

        infra_pxe_pg.center_buttons.configuration_button.click()
        add_pg = infra_pxe_pg.click_on_add_pxe_server()
        add_pg.select_depot_type("Network File System")

