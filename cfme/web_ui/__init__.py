from unittestzero import Assert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from cfme.fixtures.pytest_selenium import browser


class Region(object):
    '''
    Base class for all UI regions/pages
    '''
    def __getattr__(self, name):
        return self.locators[name]

    def __init__(self, locators={}, title=None, identifying_loc=None):
        self.locators = locators
        self.identifying_loc = identifying_loc
        self.title = title

    def is_displayed(self):
        Assert.true(self.identifying_loc is not None or
                    self.title is not None,
                    msg="Region doesn't have an identifying locator or title," +
                    "can't determine if it's current page.")
        if self.identifying_loc:
            ident_match = browser().is_displayed(self.locators[self.identifying_loc])
        else:
            ident_match = True
            if self.title:
                title_match = browser().title == self.title
            else:
                title_match = True
        return ident_match and title_match


def get_context_current_page():
    url = browser().current_url()
    stripped = url.lstrip('https://')
    return stripped[stripped.find('/'):stripped.rfind('?')]


def handle_popup(cancel=False):
    wait = WebDriverWait(browser(), 30.0)
    # throws timeout exception if not found
    wait.until(EC.alert_is_present())
    popup = browser().switch_to_alert()
    answer = 'cancel' if cancel else 'ok'
    print popup.text + " ...clicking " + answer
    popup.dismiss() if cancel else popup.accept()
