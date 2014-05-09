#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" The tab strip manipulation which appears in Configure / Configuration and possibly other pages.

Usage:

    import cfme.web_ui.tabstrip as tabs
    tabs.select_tab("Authentication")
    print is_tab_selected("Authentication")
    print get_selected_tab()

"""
from collections import Mapping

import cfme.fixtures.pytest_selenium as sel
from cfme import web_ui
from utils.log import logger


_entry_div = "//div[contains(@class, 'ui-tabs')]"  # Entry point
_entry_ul = "//ul[@id='tab' and @class='tab']"


def _root():
    """ Returns the div element encapsulating whole tab strip as an entry point.

    Returns: WebElement
    """
    return sel.first_from(_entry_div, _entry_ul)


def get_all_tabs():
    """ Return list of all tabs present.

    Returns: :py:class:`list` of :py:class:`str` Displayed names.
    """
    return [opt.text.strip().encode("utf-8") for opt in sel.elements(".//li/a", root=_root())]


def get_selected_tab():
    """ Return currently selected tab.

    Returns: :py:class:`str` Displayed name
    """
    return sel.element(".//li[@aria-selected='true' or @class='active']/a", root=_root())\
        .text\
        .strip()\
        .encode("utf-8")


def is_tab_element_selected(element):
    """ Determine whether the passed element is selected.

    This function takes the element, climbs to its parent and looks whether the
    aria-selected attribute contains true. If yes, element is selected.

    Args:
        element: WebElement with the link (a)
    Returns: :py:class:`bool`
    """
    aria = sel.element("..", root=element).get_attribute("aria-selected")
    if aria is not None:
        return "true" in aria.lower()
    else:
        return sel.element("..", root=element).get_attribute("class").lower() == "active"


def is_tab_selected(ident_string):
    """ Determine whether the element identified by passed name is selected.

    Args:
        ident_string: Identification string (displayed name) of the tab button.
    Returns: :py:class:`bool`
    """
    return is_tab_element_selected(get_clickable_tab(ident_string))


def get_clickable_tab(ident_string):
    """ Returns the relevant tab element that can be clicked on.

    Args:
        ident_string: The text diplayed on the tab.
    """
    return sel.element(".//li/a[contains(text(), '%s')]" % ident_string, root=_root())


def select_tab(ident_string):
    """ Clicks on the tab with text from ident_string.

    Clicks only if it's not actually selected.

    Args:
        ident_string: The text displayed on the tab.

    """
    if not is_tab_selected(ident_string):
        return sel.click(get_clickable_tab(ident_string))


class _TabStripField(object):
    """A form field type for use in TabStripForms"""
    def __init__(self, ident_string, arg):
        self.ident_string = ident_string
        self.arg = arg

    def locate(self):
        select_tab(self.ident_string)
        return self.arg


@web_ui.fill.method((_TabStripField, object))
def _fill_tabstrip(tabstrip_field, value):
    logger.debug(' Navigating to tabstrip %s' % value)
    web_ui.fill(tabstrip_field.locate(), value)


# In a fight between _TabStripField and object, _TabStripField should win,
# since it always delegates back to fill
web_ui.fill.prefer((_TabStripField, object), (object, Mapping))


class TabStripForm(web_ui.Form):
    """
    A class for interacting with tabstrip-contained Form elements on pages.

    This behaves exactly like a :py:class:`Form`, but is able to deal with form
    elements being broken up into tabs, accessible via a tab strip.

    Args:
        fields: A list of field name/locator tuples (same as Form implementation)
        tab_fields: A dict with tab names as keys, and each key's value being a list of
            field name/locator tuples. The ordering of fields within a tab is guaranteed
            (as it is with the normal Form) but the ordering of tabs is not guaranteed by default.
            If such ordering is needed, tab_fields can be a ``collections.OrderedDict``.
        identifying_loc: A locator which should be present if the form is visible.

    Usage:

        provisioning_form = web_ui.TabStripForm(
            tab_fields={
                'Request': [
                    ('email', '//input[@name="requester__owner_email"]'),
                    ('first_name', '//input[@id="requester__owner_first_name"]'),
                    ('last_name', '//input[@id="requester__owner_last_name"]'),
                    ('notes', '//textarea[@id="requester__request_notes"]'),
                ],
                'Catalog': [
                    ('instance_name', '//input[@name="service__vm_name"]'),
                    ('instance_description', '//textarea[@id="service__vm_description"]'),
                ]
            }
        )

    Each tab's fields will be exposed by their name on the resulting instance just like fields
    on a Form. Don't use duplicate field names in the ``tab_fields`` dict.

    Forms can then be filled in like so::

        request_info = {
            'email': 'your@email.com',
            'first_name': 'First',
            'last_name': 'Last',
            'notes': 'Notes about this request',
            'instance_name': 'An instance name',
            'instance_description': 'This is my instance!',
        }
        web_ui.fill(provisioning_form, request_info)

    """

    def __init__(self, fields=None, tab_fields=None, identifying_loc=None):
        fields = fields or list()
        for tab_ident, field in tab_fields.iteritems():
            for field_name, field_locator in field:
                fields.append((field_name, _TabStripField(tab_ident, field_locator)))
        super(TabStripForm, self).__init__(fields, identifying_loc)
