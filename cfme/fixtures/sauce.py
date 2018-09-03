import pytest
from cfme.utils.appliance import find_appliance


@pytest.mark.trylast
def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption('sauce'):
        appliance = find_appliance(item)
        browser = appliance.browser.open_browser()
        browser.execute_script("sauce:job-name={}".format(item.name))
        # todo: verify this hack, perhaps create an actual saucelabs manager in kaifuku
        browser.quit()
