#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

# TODO: This needs better tests

@pytest.mark.nondestructive #IGNORE:E1101
class TestHost:
    def test_host(self, infra_hosts_pg):
        Assert.true(infra_hosts_pg.is_the_current_page)

        for host in infra_hosts_pg.quadicon_region.quadicons:
            print "vm count: " + host.vm_count

