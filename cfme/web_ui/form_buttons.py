"""This module unifies working with CRUD form buttons.

Whenever you use Add, Save, Cancel, Reset button, use this module.
You can use it also for the other buttons with same shape like those CRUD ones.
"""
from cfme.exceptions import FormButtonNotFound
from cfme.fixtures import pytest_selenium as sel


def _locate_buttons(alt):
    """Get locator for the specific button.

    Args:
        alt: `alt` attribute of the button to look up for.
    Returns: XPath locator.
    """
    return "//img[@alt='{}' and not(contains(@class, 'dimmed'))"\
        " and contains(@class, 'button')]".format(alt)


def _get_button_element(alt):
    """Get button WebElement. Cycle through the found elements to find a visible one.

    Args:
        alt: Button's `img` `alt` attribute.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    Returns: `WebElement` with the button.
    """
    for button in sel.elements(_locate_buttons(alt)):
        if sel.is_displayed(button):
            return button
    else:
        raise FormButtonNotFound("Could not find clickable button for '{}'".format(alt))


# Functions used for operating the buttons.
# They take bogus parameters that they can be used wherever one wants.
def click_button(alt):
    """Generic function to click

    Args:
        alt: Button's `alt` attribute
    """
    return sel.click(_get_button_element(alt))


def click_func(alt):
    """Generic function factory for function to click.

    Useful for :py:class:`cfme.web_ui.Form` filling, you can generate the action with this function.

    Args:
        alt: Button's `alt` attribute
    """
    return lambda *_, **__: sel.click(_get_button_element(alt))


def add(*_, **__):
    """Click on the Add button.
    Raises: :py:class:`cfme.exceptions.FormButtonNotFound` if the specified button cannot be found.
    """
    return click_button("Add")


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
    return click_button("Cancel")


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
    return click_button("Save Changes")


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
    return click_button("Reset Changes")


def can_reset():
    """Check whether is 'Reset' button displayed == we can click on it.

    Returns: :py:class:`bool`
    """
    try:
        _get_button_element("Reset Changes")
        return True
    except FormButtonNotFound:
        return False
