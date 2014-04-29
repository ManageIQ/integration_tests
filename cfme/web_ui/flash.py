"""Provides functions for the flash area.

:var area: A :py:class:`cfme.web_ui.Region` object representing the flash region.
"""
from cfme.web_ui import Region
import cfme.fixtures.pytest_selenium as sel
from utils.log import logger

area = Region(locators=
              {'message': sel.VersionLocator(
                  {'default': '//div[starts-with(@id, "flash_") and '
                   'not(ancestor::*[contains(@style,"display: none")])]//li',
                   '9.9.9.9': '//div[starts-with(@id, "flash_") and '
                   'not(ancestor::*[contains(@style,"display: none")])]'
                   '//div[contains(@class,"alert")]'})})


class Message(object):
    """ A simple class to represent a flash error in CFME.

    Args:
        message: The message string.
        level: The level of the message.
    """
    def __init__(self, message=None, level=None):
        self.message = message
        self.level = level

    def __repr__(self):
        return "[Flash %s message '%s']" % (self.level, self.message)


def message(el):
    """ Turns an element into a :py:class:`Message` object.

    Args:
        el: The element containing the flass message.
    Returns: A :py:class:`Message` object.
    """
    return Message(message=sel.text(el),
                   level=sel.get_attribute(el, 'class'))


def get_messages():
    """Return a list of flash messages"""
    sel.wait_for_ajax()
    return map(message, sel.elements(area.message))


def dismiss():
    """Dismiss the current flash message"""
    sel.click(area.message)


def get_all_messages():
    """Returns a list of all flash messages, (including ones hidden behind
    the currently showing one, if any).  All flash messages will be
    dismissed."""
    all_messages = []
    while sel.is_displayed(area.message):
        all_messages = all_messages + get_messages()
        dismiss()
    return all_messages


def is_error(message):
    """ Checks a given message to see if is an Error.

    Args:
        message: The message object.
    """
    return any([lev in message.level for lev in ['error', 'alert-danger']])


def assert_no_errors(messages=None):
    """Asserts that there are no current Error messages. If no messages
    are passed in, they will be retrieved from the UI."""

    all_messages = messages or get_messages()
    errors = filter(is_error, all_messages)
    if errors:
        raise Exception(errors)
    else:
        return all_messages


def assert_message_match(m):
    """ Asserts that a message matches a specific string."""
    logger.debug('Asserting flash message match for "{}"'.format(m))
    if not any([fm.message == m for fm in get_messages()]):
        logger.debug(' No match found in...{}'.format(get_messages()))
        raise Exception("No matching flash message for '%s'" % m)


def assert_message_contain(m):
    """ Asserts that a message contains a specific string """
    if not any([m in fm.message for fm in get_messages()]):
        raise Exception("No flash message contains '%s'" % m)


def assert_success_message(m):
    """Asserts that there are no errors and a (green) info message
    matches the given string."""
    messages = get_messages()
    assert_no_errors(messages)
    if not any([(fm.message == m and fm.level == 'info') for fm in messages]):
        raise Exception("No matching info flash message for '%s'" % m)
