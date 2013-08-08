# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
import os

# TODO: get import files via http
@pytest.fixture(scope="module",
                params=["datastore.xml"])
def import_automate_file(request):
    automate_file = "%s/tests/ui/automate/%s" % (os.getcwd(), request.param)
    return automate_file

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAutomate:
    def test_import_automate(self, automate_importexport_pg, import_automate_file):
        Assert.true(automate_importexport_pg.is_the_current_page)
        automate_importexport_pg = automate_importexport_pg\
                .import_automate(import_automate_file)
        Assert.equal(automate_importexport_pg.flash.message,
                "Import file was uploaded successfully",
                "Flash message not matched")

