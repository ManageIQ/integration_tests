import pytest

from cfme.utils.browser import manager


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption('sauce'):
        manager.ensure_open()
        manager.browser().execute_script(f"sauce:job-name={item.name}")
        manager.quit()
