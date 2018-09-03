"""Core functionality for starting, restarting, and stopping a selenium browser."""
import atexit
from collections import namedtuple

from selenium.common.exceptions import WebDriverException

ScreenShot = namedtuple("screenshot", ['png', 'error'])


def take_screenshot(driver):
    screenshot = None
    screenshot_error = None
    try:
        screenshot = driver.get_screenshot_as_base64()
    except (AttributeError, WebDriverException):
        # See comments utils.browser.ensure_browser_open for why these two exceptions
        screenshot_error = 'browser error'
    except Exception as ex:
        # If this fails for any other reason,
        # leave out the screenshot but record the reason
        if str(ex):
            screenshot_error = '{}: {}'.format(type(ex).__name__, str(ex))
        else:
            screenshot_error = type(ex).__name__
    return ScreenShot(screenshot, screenshot_error)
