import pytest

from cfme.utils.appliance import find_appliance


@pytest.mark.trylast
def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption('sauce'):
        appliance = find_appliance(item)
        driver = appliance.browser.open_browser()
        driver.execute_script("sauce:job-name={}".format(item.name))
        appliance.browser.quit_browser()
