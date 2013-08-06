# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAutomate:
    def test_export_automate(self, automate_importexport_pg):
        Assert.true(automate_importexport_pg.is_the_current_page)
        automate_importexport_pg = automate_importexport_pg.export_automate()
        # no confirmation flash message to assert

