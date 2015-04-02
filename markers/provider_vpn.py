# -*- coding: utf-8 -*-
import pytest


@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    for item in items:
        if "provider_crud" in item.fixturenames:
            mark = pytest.mark.usefixtures("provider_vpn")
            item.add_marker(mark)
