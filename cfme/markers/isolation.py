"""Marker for browser isolation on specific tests"""
import pytest

from cfme.test_framework.browser_isolation import browser_implementation_quits
from cfme.utils.log import logger


# Add Marker
def pytest_configure(config):
    config.addinivalue_line('markers', 'browser_isolation: Mark a test case for browser isolation')


@pytest.mark.hookwrapper(tryfirst=True)
def pytest_runtest_setup(item):
    if item.get_marker('browser_isolation'):
        logger.info('Browser isolation for marker in setup')
        browser_implementation_quits(item)
    yield


@pytest.mark.hookwrapper(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    if item.get_marker("browser_isolation"):
        logger.info('Browser isolation for marker in teardown')
        browser_implementation_quits(item)
