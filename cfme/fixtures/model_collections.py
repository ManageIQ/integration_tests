# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(scope='function')
def dashboards(appliance):
    from cfme.dashboard import DashboardCollection
    return DashboardCollection(appliance=appliance)
