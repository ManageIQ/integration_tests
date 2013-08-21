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

        templates_pg = infra_pxe_pg.click_on_customization_templates()
        rhel_pxe_pg = templates_pg.click_on_examples_rhel_pxe()
        copy_template_pg = rhel_pxe_pg.click_on_copy_template()
        template_data = dict(
          name='test_name',
          description='test_description',
          image_type='RHEL-6',
          template_type='Kickstart')
        copy_template_pg.fill_data(**template_data)
        cancel_pg = copy_template_pg.click_on_cancel()
        flash_message = "Add of new Customization Template was cancelled by the user"
        Assert.equal(cancel_pg.flash.message, flash_message, cancel_pg.flash.message)

