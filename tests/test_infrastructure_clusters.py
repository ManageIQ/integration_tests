'''
@author: Unknown
'''
# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive #IGNORE:E1101
def test_cluster(infra_clusters_pg):
    Assert.true(infra_clusters_pg.is_the_current_page)
    detail_pg = infra_clusters_pg.click_cluster("iscsi in iscsi")
    print detail_pg.name, detail_pg.provider, \
            detail_pg.datacenter, detail_pg.host_count

