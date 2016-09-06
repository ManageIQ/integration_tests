# -*- coding: utf-8 -*-
"""Module handling the history button.

:var HISTORY_ITEMS: Locator that finds all the history items from dropdown
:var SINGLE_HISTORY_BUTTON: Locator that finds the history button if it is without the dropdown.
"""
from cfme.fixtures import pytest_selenium as sel
from . import toolbar


HISTORY_ITEMS = (
    '//button[following-sibling::ul and ./i[contains(normalize-space(@class), "fa-arrow-left")]]'
    '/following-sibling::ul/li/a')
SINGLE_HISTORY_BUTTON = (
    '//button[not(following-sibling::ul) and '
    './i[contains(normalize-space(@class), "fa-arrow-left")]]')


def single_button():
    """Returns the textual contents of the single history button. If not present, None is returned.
    """
    if not sel.is_displayed(SINGLE_HISTORY_BUTTON):
        return None
    return sel.get_attribute(SINGLE_HISTORY_BUTTON, 'title')


def dropdown_history_items():
    """Returns a list of strings representing the items from dropdown. Empty if not present"""
    return map(sel.text, sel.elements(HISTORY_ITEMS))


def any_history_present():
    """Returns if the single history button or the dropdown is present."""
    return bool(single_button() or dropdown_history_items())


def history_items_present():
    """Checks if the history items are present, returns bool"""
    return bool(dropdown_history_items())


def single_button_present():
    """Checks if the single history button is present, returns bool"""
    return bool(single_button())


def history_items():
    """Returns a list of all history items on the page."""
    sb = single_button()
    if sb:
        return [sb]
    else:
        return dropdown_history_items()


def select_history_item(text):
    """Handles selecting the history item by text using the toolbar module."""
    sb = single_button()
    if sb is not None:
        # No dropdown items
        if sb != text:
            raise ValueError('There is no such history button: {!r}'.format(text))
        return toolbar.select(text)
    else:
        # There are dropdown items
        di = dropdown_history_items()
        if text not in di:
            raise ValueError('There is no such history button: {!r}'.format(text))
        return toolbar.select('History', text)


def select_nth_history_item(n):
    """Handles selecting the history items by the position. 0 is the latest (top one)."""
    try:
        return select_history_item(history_items()[n])
    except KeyError:
        raise KeyError(
            'There are only {} history items, you wanted the {}th'.format(len(history_items(), n)))
