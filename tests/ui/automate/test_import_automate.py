# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.fixture
def data_dir_path(request):
    '''Returns the corresponding data dir'''
    return (request.fspath.dirname).replace("/tests/", "/data/")

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
def test_import_automate(automate_importexport_pg, data_dir_path):
    Assert.true(automate_importexport_pg.is_the_current_page)
    automate_importexport_pg = automate_importexport_pg\
            .import_automate("%s/%s" % (data_dir_path, "ds2.xml"))
    Assert.equal(automate_importexport_pg.flash.message,
            "Datastore import was successful",
            "Flash message not matched")

    # cleanup by resetting to default
    automate_importexport_pg = automate_importexport_pg.reset_automate()
    Assert.equal(automate_importexport_pg.flash.message,
            "All custom classes and instances have been reset to default",
            "Flash message not matched")

