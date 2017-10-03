# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(scope='function')
def dashboards(appliance):
    from cfme.dashboard import DashboardCollection
    return DashboardCollection(appliance=appliance)


@pytest.fixture(scope="module")
def objects(appliance, provider):
    from cfme.storage.object_store_object import ObjectStoreObjectCollection
    collection = ObjectStoreObjectCollection(appliance=appliance)
    objects = collection.all(provider)
    return [collection, objects]