"""This module unifies working with CRUD form buttons.

Whenever you use Add, Save, Cancel, Reset button, use this module.
You can use it also for the other buttons with same shape like those CRUD ones.
"""
from selenium.common.exceptions import NoSuchElementException

from cfme.fixtures import pytest_selenium as sel


class FormButton(object):
    """This class reresents the small black button usually located in forms or CRUD.

    Args:
        alt: The text from `alt` field of the image
    """
    def __init__(self, alt):
        self._alt = alt

    def locate(self):
        """This hairy locator ensures that the button is not dimmed and not hidden."""
        return ("//img[@alt='{}' and not(contains(@class, 'dimmed')) and contains(@class, 'button')"
            "and not(ancestor::*[contains(@style, 'display:none')"
            " or contains(@style, 'display: none')])]".format(self._alt))

    @property
    def can_be_clicked(self):
        """Whether the button is displayed, therefore clickable."""
        try:
            sel.move_to_element(self)
            return sel.is_displayed(self)
        except NoSuchElementException:
            return False

    def __call__(self, *args, **kwargs):
        """For maintaining backward compatibility"""
        return sel.click(self)

    def __str__(self):
        return self.locate()

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, str(repr(self._alt)))

add = FormButton("Add")
save = FormButton("Save Changes")
cancel = FormButton("Cancel")
reset = FormButton("Reset Changes")
