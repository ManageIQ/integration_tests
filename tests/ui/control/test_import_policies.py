# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
import os

# TODO: get import files via http
@pytest.fixture(scope="module",
                params=["policies.yaml"])
def import_policy_file(request):
    policy_file = "%s/tests/ui/control/%s" % (os.getcwd(), request.param)
    return policy_file

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestControl:
    def test_import_policies(self, control_importexport_pg, import_policy_file):
        Assert.true(control_importexport_pg.is_the_current_page)
        control_importexport_pg = control_importexport_pg.import_policies(
                import_policy_file)
        Assert.equal(control_importexport_pg.flash.message,
                "Press commit to Import")
        control_importexport_pg = control_importexport_pg.click_on_commit()
        Assert.equal(control_importexport_pg.flash.message,
                "Import file was uploaded successfully")

