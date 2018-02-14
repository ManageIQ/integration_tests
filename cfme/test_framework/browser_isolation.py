# -*- coding: utf-8 -*-
"""Plugin enabling us to isolate browser sessions per test."""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        '--browser-isolation',
        action='store_true',
        default=False,
        help='Isolate browser sessions for each test.')


@pytest.mark.hookwrapper(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    if item.config.getoption("browser_isolation"):
        holder = item.config.pluginmanager.getplugin('appliance-holder')
        if holder:
            appliance = holder.held_appliance
            for implementation in [appliance.browser, appliance.ssui]:
                implementation.quit_browser()
