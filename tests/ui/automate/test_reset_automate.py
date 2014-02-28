# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
import time


@pytest.mark.destructive
@pytest.mark.usefixtures("maximized")
@pytest.mark.fixtureconf(server_roles='+automate')
class TestAutomate:
    def test_reset_automate(self, server_roles, automate_importexport_pg):
        # if server role was just enable, we need to give the service time to start
        #    we need to come up with a way to query a worker thread, this works for today
        time.sleep(90)
        Assert.true(automate_importexport_pg.is_the_current_page)
        automate_importexport_pg = automate_importexport_pg.reset_automate()
        Assert.equal(automate_importexport_pg.flash.message,
            "All custom classes and instances have been reset to default",
            "Flash message not matched")
