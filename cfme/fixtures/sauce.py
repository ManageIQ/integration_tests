import pytest


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption('sauce'):
        from cfme.utils.browser import ensure_browser_open, quit, browser
        ensure_browser_open()
        browser().execute_script(f"sauce:job-name={item.name}")
        quit()
