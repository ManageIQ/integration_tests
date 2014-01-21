from cfme.web_ui import Region
from selenium.webdriver.common.by import By
import cfme.fixtures.pytest_selenium as sel

area = Region(locators=
              {'message': (By.XPATH, "//div[@id='flash_text_div' or @id='flash_div']//li")})


class Message(object):
    def __init__(self, message=None, level=None):
        self.message = message
        self.level = level

    def __repr__(self):
        return "[Flash %s message '%s']" % (self.level, self.message)


def message(el):
    return Message(message=sel.text(el),
                   level=sel.get_attribute(el, 'class'))


def get_messages():
    '''Return a list of flash messages'''
    sel.wait_for_ajax()
    return map(message, sel.elements(area.message))


def is_error(message):
    return message.level == 'error'


def assert_no_errors():
    all_messages = get_messages()
    errors = filter(is_error, all_messages)
    if errors:
        raise Exception(errors)
    else:
        return all_messages


def assert_message_match(m):
    if not any([fm.message == m for fm in get_messages()]):
        raise Exception("No matching flash message for '%s'" % m)
