#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive #IGNORE:E1101
class TestDatastore:
    def test_datastore(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        ds_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Datastores").click()
        Assert.true(ds_pg.is_the_current_page)
        for datastore in ds_pg.quadicon_region.quadicons:
            print datastore.title + " VMs: %s, Hosts: %s" % (datastore.vm_count, datastore.host_count)
        details_pg = ds_pg.click_datastore("datastore1")
        print details_pg.name, details_pg.ds_type
        time.sleep(1)
        edit_tags_pg = ds_pg.click_on_edit_tags()
        time.sleep(1)

