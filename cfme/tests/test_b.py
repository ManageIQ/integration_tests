from cfme import login
from utils import appliance
from utils import browser
from cfme.fixtures import pytest_selenium as sel
from utils.log import logger


def test_munch():
    browser.start()
    login.login_admin()
    logger.debug(sel.current_url())
    with appliance.IPAppliance('10.8.59.211'):
        browser.start()
        login.login_admin()
        logger.debug(sel.current_url())
    browser.start()
    logger.debug(sel.current_url())
