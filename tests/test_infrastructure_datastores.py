#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive #IGNORE:E1101
class TestDatastore:
    def test_datastore(self, infra_datastores_pg):
        Assert.true(infra_datastores_pg.is_the_current_page)
        for datastore in infra_datastores_pg.quadicon_region.quadicons:
            print datastore.title + " VMs: %s, Hosts: %s"\
                    % (datastore.vm_count, datastore.host_count)
        details_pg = infra_datastores_pg.click_datastore("datastore1")
        print details_pg.name, details_pg.ds_type
        infra_datastores_pg.click_on_edit_tags()

