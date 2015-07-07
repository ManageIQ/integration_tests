# -*- coding: utf-8 -*-
"""Provides functions for the flash area.

:var area: A :py:class:`cfme.web_ui.Region` object representing the flash region.
"""
from functools import wraps

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import CFMEExceptionOccured, FlashMessageException
from cfme.web_ui import Region
from utils import version
from utils.log import logger
from utils.pretty import Pretty

area = Region(
    locators={
        'message': {
            version.LOWEST: ' | '.join([
                ('//div[starts-with(@id, "flash_") and '
                    'not(ancestor::*[contains(@style,"display: none")])]//li'),
                '//div[@id="flash_div"]',  # login screen
            ]),
            '5.3': ' | '.join([
                ('//div[starts-with(@id, "flash_") and '
                    'not(ancestor::*[contains(@style,"display: none")])]'
                    '//div[contains(@class,"alert")]'),
                '//div[@id="flash_div"]',  # login screen
            ])
        }
    }
)

_mapping_new = {
    "alert-warning": "warning",
    "alert-success": "success",
    "alert-danger": "error",
    "alert-info": "info"
}


class Message(Pretty):
    """ A simple class to represent a flash error in CFME.

    Args:
        message: The message string.
        level: The level of the message.
    """
    pretty_attrs = ['message', 'level']

    def __init__(self, message=None, level=None):
        self.message = message
        self.level = level


@version.dependent
def get_message_level(el):
    return sel.get_attribute(el, "class") or "error"


@get_message_level.method(version.LATEST)
def get_message_level_up(el):
    _class = sel.get_attribute(el, "class")
    for key, value in _mapping_new.iteritems():
        if key in _class:
            return value
    return "error"


@version.dependent
def get_message_text(el):
    strong = sel.elements("./strong", root=el)
    if strong:
        return sel.text(strong[0])
    else:
        return sel.text(el)


@get_message_text.method(version.LATEST)
def get_message_text_up(el):
    return sel.text(el)


def message(el):
    """ Turns an element into a :py:class:`Message` object.

    Args:
        el: The element containing the flass message.
    Returns: A :py:class:`Message` object.
    """
    return Message(message=get_message_text(el),
                   level=get_message_level(el))  # no class attr on login screen


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
    """ Checks a given message to see if is an Error.'

    Args:
        message: The message object.
    """
    return message.level in ('error',)


def verify_rails_error(f):
    # Wrapper that checks the rails error before the flash message
    @wraps(f)
    def g(*args, **kwargs):
        sel.wait_for_ajax()  # Just in case
        error = sel.get_rails_error()
        if error is not None:
            raise CFMEExceptionOccured(
                "Flash message check failed because of following rails error:\n{}".format(error))
        return f(*args, **kwargs)
    return g


@verify_rails_error
def assert_no_errors(messages=None):
    """Asserts that there are no current Error messages. If no messages
    are passed in, they will be retrieved from the UI."""

    all_messages = messages or get_messages()
    errors = [error.message for error in filter(is_error, all_messages)]
    if errors:
        raise FlashMessageException(', '.join(errors))
    else:
        return all_messages


@verify_rails_error
def assert_message_match(m):
    """ Asserts that a message matches a specific string."""
    logger.debug('Asserting flash message match for "{}"'.format(m))
    if not any([fm.message == m for fm in get_messages()]):
        logger.debug(' No match found in...{}'.format(get_messages()))
        raise FlashMessageException("No matching flash message for '%s'" % m)


@verify_rails_error
def assert_message_contain(m):
    """ Asserts that a message contains a specific string """
    if not any([m in fm.message for fm in get_messages()]):
        raise FlashMessageException("No flash message contains '%s'" % m)


@verify_rails_error
def assert_success_message(m):
    """Asserts that there are no errors and a (green) info message
    matches the given string."""
    messages = get_messages()
    assert_no_errors(messages)
    if not any([
            (fm.message == m and (fm.level in {"info", "success"}))
            for fm
            in messages]):
        raise FlashMessageException(
            "No matching info flash message for '{}', instead got {}".format(m, messages))
