# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(scope='function')
def dashboards(appliance):
    from cfme.dashboard import DashboardCollection
    return DashboardCollection(appliance=appliance)


@pytest.fixture(scope="function")
def objects(appliance):
    from cfme.storage.object_store_object import ObjectStoreObjectCollection
    return ObjectStoreObjectCollection(appliance=appliance)
