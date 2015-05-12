"""This module unifies working with CRUD form buttons.

Whenever you use Add, Save, Cancel, Reset button, use this module.
You can use it also for the other buttons with same shape like those CRUD ones.
"""
from selenium.common.exceptions import NoSuchElementException
from xml.sax.saxutils import quoteattr

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill
from utils.log import logger
from utils.pretty import Pretty


class FormButton(Pretty):
    """This class represents the buttons usually located in forms or CRUD.

    Args:
        alt: The text from ``alt`` field of the image.
        dimmed_alt: In case the ``alt`` param is different in the dimmed variant of the button.
        force_click: Click always, even if it is dimmed. (Causes an error if not visible)
        partial_alt: Whether the alt matching should be only partial (``in``).
    """
    pretty_attrs = ['_alt', '_dimmed_alt', '_force', '_partial']

    def __init__(self, alt, dimmed_alt=None, force_click=False, partial_alt=False):
        self._alt = alt
        self._dimmed_alt = dimmed_alt
        self._force = force_click
        self._partial = partial_alt

    def alt_expr(self, dimmed=False):
        if self._partial:
            return "(contains(normalize-space(@alt), {}))".format(
                quoteattr((self._dimmed_alt or self._alt) if dimmed else self._alt))
        else:
            return "(normalize-space(@alt)={})".format(
                quoteattr((self._dimmed_alt or self._alt) if dimmed else self._alt))

    def locate(self):
        """This hairy locator ensures that the button is not dimmed and not hidden."""
        return ("(//a | //button | //img | //input)[{} and not(contains(@class, 'dimmed'))"
                " and (contains(@class, 'button') or contains(@class, 'btn')"
                " or contains(@src, 'button'))"
                " and not(ancestor::*[contains(@style, 'display:none')"
                " or contains(@style, 'display: none')])]".format(self.alt_expr(dimmed=False)))

    @property
    def is_dimmed(self):
        return sel.is_displayed("(//a | //button | //img | //input)[{}"
            " and contains(@class, 'dimmed')"
            " and (contains(@class, 'button') or contains(@class, 'btn')"
            " or contains(@src, 'button'))"
            " and not(ancestor::*[contains(@style, 'display:none')"
            " or contains(@style, 'display: none')])]|//button[normalize-space(.)='{}' and"
            " (@disabled='true' or contains(@class, 'btn-disabled'))"
            " and not(ancestor::*[contains(@style, 'display:none')"
            " or contains(@style, 'display: none')])]".format(
                self.alt_expr(dimmed=True), self._dimmed_alt or self._alt
            ))

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
        sel.click(self)

    def _custom_click_handler(self):
        """Handler called from pytest_selenium"""
        sel.wait_for_ajax()
        if self.is_dimmed and not self._force:
            logger.info("Not clicking {} because it is dimmed".format(str(repr(self))))
            return
        sel.wait_for_element(self, timeout=5)
        return sel.click(self, no_custom_handler=True)

    def __str__(self):
        return self.locate()

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, str(repr(self._alt)))

add = FormButton("Add")
save = FormButton("Save Changes", dimmed_alt="Save")
cancel = FormButton("Cancel")
submit = FormButton("Submit")
reset = FormButton("Reset Changes", dimmed_alt="Reset")
validate = FormButton("Validate the credentials by logging into the Server", dimmed_alt="Validate")
validate_short = FormButton("Validate the credentials")
host_provision_submit = FormButton("Submit this provisioning request")
host_provision_cancel = FormButton("Cancel this provisioning request")


@fill.method((FormButton, bool))
def _fill_fb_bool(fb, b):
    if b:
        sel.click(fb)
