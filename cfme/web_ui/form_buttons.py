"""This module unifies working with CRUD form buttons.

Whenever you use Add, Save, Cancel, Reset button, use this module.
You can use it also for the other buttons with same shape like those CRUD ones.
"""
from selenium.common.exceptions import NoSuchElementException
from xml.sax.saxutils import quoteattr

from widgetastic.xpath import quote

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill
from utils import version
from utils.log import logger
from utils.pretty import Pretty


class FormButton(Pretty):
    """This class represents the buttons usually located in forms or CRUD.

    Args:
        alt: The text from ``alt`` field of the image.
        dimmed_alt: In case the ``alt`` param is different in the dimmed variant of the button.
        force_click: Click always, even if it is dimmed. (Causes an error if not visible)
        partial_alt: Whether the alt matching should be only partial (``in``).
        ng_click: To match the angular buttons, you can use this to specify the contents of
            ``ng-click`` attributeh.
    """
    pretty_attrs = ['_alt', '_dimmed_alt', '_force', '_partial', '_ng_click']

    PRIMARY = 'btn-primary'

    class Button:
        """Holds pieces of the XPath to be assembled."""
        TAG_TYPES = "//a | //button | //img | //input"
        TYPE_CONDITION = (
            "(contains(@class, 'button') or contains(@class, 'btn') or contains(@src, 'button'))"
        )
        DIMMED = "(contains(@class, 'dimmed') " \
            "or contains(@class, 'disabled') " \
            "or contains(@class, 'btn-disabled'))"
        NOT_DIMMED = "not{}".format(DIMMED)
        IS_DISPLAYED = (
            "not(ancestor::*[contains(@style, 'display:none') "
            "or contains(@style, 'display: none')])")
        ON_CURRENT_TAB = (
            "not(ancestor::div[contains(@class, 'tab-pane') and not(contains(@class, 'active'))])")

    def __init__(
            self, alt, dimmed_alt=None, force_click=False, partial_alt=False, ng_click=None,
            classes=None):
        self._alt = alt
        self._dimmed_alt = dimmed_alt
        self._force = force_click
        self._partial = partial_alt
        self._ng_click = ng_click
        self._classes = classes or []

    def alt_expr(self, dimmed=False):
        if self._partial:
            if self._ng_click is None:
                return (
                    "(contains(normalize-space(@alt), {alt}) or "
                    "contains(normalize-space(text()), {alt}))".format(
                        alt=quoteattr((self._dimmed_alt or self._alt) if dimmed else self._alt)))
            else:
                return (
                    "(contains(normalize-space(@alt), {alt}) or "
                    "@ng-click={click} or "
                    "contains(normalize-space(text()), {alt}))".format(
                        alt=quoteattr((self._dimmed_alt or self._alt) if dimmed else self._alt),
                        click=quoteattr(self._ng_click)))
        else:
            if self._ng_click is None:
                return (
                    "(normalize-space(@alt)={alt} or "
                    "normalize-space(text())={alt})".format(
                        alt=quoteattr((self._dimmed_alt or self._alt) if dimmed else self._alt)))
            else:
                return (
                    "(normalize-space(@alt)={alt} or "
                    "@ng-click={click} or "
                    "normalize-space(text())={alt})".format(
                        alt=quoteattr((self._dimmed_alt or self._alt) if dimmed else self._alt),
                        click=quoteattr(self._ng_click)))

    def _format_generator(self, dimmed=False, include_dimmed_alt=False):
        """Generates a dict that will be passed to the formatting strings."""
        d = {}
        for key, value in self.Button.__dict__.iteritems():
            if not key.startswith("_"):
                d[key] = value
        d["ALT_EXPR"] = self.alt_expr(dimmed=dimmed)
        if include_dimmed_alt:
            d["DIMMED_ALT"] = quoteattr(self._dimmed_alt or self._alt)
        if self._classes:
            d['CLASSES'] = 'and ({})'.format(
                ' and '.join('contains(@class, {})'.format(quote(kls)) for kls in self._classes))
        else:
            d['CLASSES'] = ''
        return d

    def locate(self):
        return (
            "({TAG_TYPES})[{ALT_EXPR} and {NOT_DIMMED} and {TYPE_CONDITION} and {IS_DISPLAYED} "
            "and {ON_CURRENT_TAB} {CLASSES}]"
            .format(**self._format_generator(dimmed=False)))

    @property
    def is_dimmed(self):
        locator = (
            "({TAG_TYPES})[{ALT_EXPR} and {DIMMED} and {TYPE_CONDITION} and {IS_DISPLAYED} "
            "and {ON_CURRENT_TAB} {CLASSES}]"
            "|"  # A bit different type of a button
            "({TAG_TYPES})[normalize-space(.)={DIMMED_ALT} and {IS_DISPLAYED} and "
            "(@disabled='true' or contains(@class, 'btn-disabled')) and {ON_CURRENT_TAB}]"
            .format(**self._format_generator(dimmed=True, include_dimmed_alt=True)))
        return sel.is_displayed(locator)

    @property
    def can_be_clicked(self):
        """Whether the button is displayed, therefore clickable."""
        try:
            return sel.is_displayed(self, move_to=True)
        except NoSuchElementException:
            return False

    def __call__(self, *args, **kwargs):
        """For maintaining backward compatibility"""
        sel.click(self)

    def _custom_click_handler(self, wait_ajax):
        """Handler called from pytest_selenium"""
        if self.is_dimmed and not self._force:
            logger.error("Could not click %s because it was dimmed", repr(self))
            return
        sel.wait_for_element(self, timeout=5)
        return sel.click(self, no_custom_handler=True, wait_ajax=wait_ajax)

    def __str__(self):
        return self.locate()

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(repr(self._alt)))


add = FormButton("Add")
save = FormButton("Save Changes", dimmed_alt="Save", ng_click="saveClicked()")
simple_save = FormButton("Save")
angular_save = FormButton("Save changes", ng_click="saveClicked()")
cancel = FormButton("Cancel")
cancel_changes = FormButton("Cancel Changes")
submit = FormButton("Submit")
reset = FormButton("Reset Changes", dimmed_alt="Reset")
validate = FormButton("Validate the credentials by logging into the Server", dimmed_alt="Validate")
validate_short = FormButton("Validate the credentials")
validate_multi_host = FormButton("Validate the credentials by logging into the selected Host")
host_provision_submit = FormButton("Submit this provisioning request")
host_provision_cancel = FormButton("Cancel this provisioning request")
retrieve = FormButton("LDAP Group Lookup")
apply_filters = FormButton("Apply Filters", ng_click="dash.applyFilters()")

_stored_pw_script = '//a[contains(@id, "change_stored_password")]'
_stored_pw_angular = "//a[contains(@ng-hide, 'bChangeStoredPassword')]"


def change_stored_password():
    if version.current_version() > '5.5':
        if sel.is_displayed(_stored_pw_script):
            sel.execute_script(
                sel.get_attribute(
                    sel.element(_stored_pw_script), 'onClick'))
            sel.wait_for_ajax()  # To play safe
        elif sel.is_displayed(_stored_pw_angular):
            sel.click(_stored_pw_angular)
        else:
            logger.info("Probably no creds")


@fill.method((FormButton, bool))
def _fill_fb_bool(fb, b):
    if b:
        sel.click(fb)
