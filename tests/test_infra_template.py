#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestInfrastructurePXETemplate:
    def test_infrastructure_pxe_template(self, infra_pxe_pg):
        Assert.true(infra_pxe_pg.is_the_current_page)

        error_text = "There should be 4 accordion items instead of %s" \
                % len(infra_pxe_pg.accordion_region.accordion_items)
        Assert.equal(len(infra_pxe_pg.accordion_region.accordion_items),
                4, error_text)

        infra_pxe_pg.accordion_region.accordion_by_name(
                "Customization Templates").click()
        infra_pxe_pg.accordion_region.current_content.children[0]\
                .twisty.expand()
        infra_pxe_pg.accordion_region.current_content.children[0]\
                .children[2].click()

        #This needs to be here. Configuration button is not clickable immediately.
        # TODO: This needs to be fixed. No sleeps please
        time.sleep(1)
        infra_pxe_pg.center_buttons.configuration_button.click()
