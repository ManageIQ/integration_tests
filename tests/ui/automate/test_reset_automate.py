# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
class TestAutomate:
    def test_reset_automate(self, automate_importexport_pg):
        Assert.true(automate_importexport_pg.is_the_current_page)
        automate_importexport_pg = automate_importexport_pg.reset_automate()
        Assert.equal(automate_importexport_pg.flash.message,
                "All custom classes and instances have been reset to default",
                "Flash message not matched")

