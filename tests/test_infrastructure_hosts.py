#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive #IGNORE:E1101
class TestHost:
    def test_host(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        hosts_pg = home_pg.header.site_navigation_menu("Infrastructure").sub_navigation_menu("Hosts").click()
        Assert.true(hosts_pg.is_the_current_page)

        for host in hosts_pg.quadicon_region.quadicons:
            print "vm count: " + host.vm_count

