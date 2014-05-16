"""This module unifies working with CRUD form buttons.

Whenever you use Add, Save, Cancel, Reset button, Use this module.
"""
from cfme.exceptions import FormButtonNotFound
from cfme.fixtures import pytest_selenium as sel


def _locate_buttons(title):
    """Get locator for the specific button.

    Args:
        title: `title` attribute of the button to look up for.
    Returns: XPath locator.
    """
    return "//img[@title='{}' and not(contains(@class, 'dimmed'))"\
        " and contains(@class, 'button')]".format(title)


def _get_button_element(title):
    """Get button WebElement. Cycle through the found elements to find a visible one.

    Args:
        title: Button's `img` `title` attribute.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    Returns: `WebElement` with the button.
    """
    for button in sel.elements(_locate_buttons(title)):
        if sel.is_displayed(button):
            return button
    else:
        raise FormButtonNotFound("Could not find clickable button for '{}'".format(title))


# Functions used for operating the buttons.
# They take bogus parameters that they can be used wherever one wants.
def add(*_, **__):
    """Click on the Add button.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    """
    return sel.click(_get_button_element("Add"))


def can_add():
    """Check whether is 'Add' button displayed == we can click on it.

    Returns: :py:class:`bool`
    """
    try:
        _get_button_element("Add")
        return True
    except FormButtonNotFound:
        return False


def cancel(*_, **__):
    """Click on the Cancel button.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    """
    return sel.click(_get_button_element("Cancel"))


def can_cancel():
    """Check whether is 'Cancel' button displayed == we can click on it.

    Returns: :py:class:`bool`
    """
    try:
        _get_button_element("Cancel")
        return True
    except FormButtonNotFound:
        return False


def save(*_, **__):
    """Click on the Save button.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    """
    return sel.click(_get_button_element("Save Changes"))


def can_save():
    """Check whether is 'Save' button displayed == we can click on it.

    Returns: :py:class:`bool`
    """
    try:
        _get_button_element("Save Changes")
        return True
    except FormButtonNotFound:
        return False


def reset(*_, **__):
    """Click on the Reset button.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    """
    return sel.click(_get_button_element("Reset Changes"))


def can_reset():
    """Check whether is 'Reset' button displayed == we can click on it.

    Returns: :py:class:`bool`
    """
    try:
        _get_button_element("Reset Changes")
        return True
    except FormButtonNotFound:
        return False
