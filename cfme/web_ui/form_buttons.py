"""This module unifies working with CRUD form buttons"""
from cfme.exceptions import FormButtonNotFound
from cfme.fixtures import pytest_selenium as sel


def _locate_buttons(title):
    """Get locator for the specific button."""
    return "//img[@title='{}' and not(contains(@class, 'dimmed'))"\
        " and contains(@class, 'button')]".format(title)


def _get_button_element(title):
    """Get button WebElement. Cycle through the found elements to find a visible one.

    Args:
        title: Button's `img` `title` attribute.
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
    return sel.click(_get_button_element("Add"))


def cancel(*_, **__):
    return sel.click(_get_button_element("Cancel"))


def save(*_, **__):
    return sel.click(_get_button_element("Save Changes"))


def reset(*_, **__):
    return sel.click(_get_button_element("Reset Changes"))
