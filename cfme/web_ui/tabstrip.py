# -*- coding: utf-8 -*-
""" The tab strip manipulation which appears in Configure / Configuration and possibly other pages.

Usage:

    import cfme.web_ui.tabstrip as tabs
    tabs.select_tab("Authentication")
    print(is_tab_selected("Authentication"))
    print(get_selected_tab())

"""
from collections import Mapping

import cfme.fixtures.pytest_selenium as sel
from cfme import web_ui
from utils.log import logger
from utils.pretty import Pretty

# Entry point
# There have been different types of the entry points throughout the history, sometimes even
# different versions in one build.
_entry_loc = "|".join([
    "//div[contains(@class, 'ui-tabs')]",
    "//ul[contains(@class, 'nav-tabs')]",
    "//ul[contains(@class, 'ui-tabs-nav') or @class='tab2' or @class='tab3']",
    "//ul[@id='tab' and @class='tab']"])


def _root():
    """ Returns the div element encapsulating whole tab strip as an entry point.

    Returns: :py:class:`list` of :py:class:`cfme.fixtures.pytest_selenium.WebElement`.
    """
    return sel.elements(_entry_loc)


def get_all_tabs():
    """ Return list of all tabs present.

    Returns: :py:class:`list` of :py:class:`str` Displayed names.
    """
    return [opt.text.strip().encode("utf-8") for opt in sel.elements(".//li/a", root=_root())]


def get_selected_tab():
    """ Return currently selected tab.

    Returns: :py:class:`str` Displayed name
    """
    return sel.element(
        ".//li[@aria-selected='true' or contains(@class, 'active')]/a", root=_root())\
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
        return sel.element("..", root=element)\
                  .get_attribute("class")\
                  .lower() in {"active", "active-single"}


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
    return sel.element(
        ".//li/a[contains(normalize-space(text()), '%s')]" % ident_string, root=_root())


def select_tab(ident_string):
    """ Clicks on the tab with text from ident_string.

    Clicks only if it's not actually selected.

    Args:
        ident_string: The text displayed on the tab.

    """
    if not is_tab_selected(ident_string):
        return sel.click(get_clickable_tab(ident_string))


class _TabStripField(Pretty):
    """A form field type for use in TabStripForms"""

    pretty_attrs = ['ident_string', 'arg']

    def __init__(self, ident_string, arg):
        self.ident_string = ident_string
        self.arg = arg

    def locate(self):
        select_tab(self.ident_string)
        return self.arg


@web_ui.fill.method((_TabStripField, object))
def _fill_tabstrip(tabstrip_field, value):
    logger.debug(' Navigating to tabstrip "{}"'.format(tabstrip_field.ident_string))
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
        order: If specified, specifies order of the tabs. Can be lower number than number of tabs,
            remaining values will be complemented.
        fields_end: Same as fields, but these are appended at the end of generated fields instead.

    Usage:

        provisioning_form = web_ui.TabStripForm(
            tab_fields={
                'Request': [
                    ('email', Input("requester__owner_email")),
                    ('first_name', Input("requester__owner_first_name")),
                    ('last_name', Input("requester__owner_last_name")),
                    ('notes', '//textarea[@id="requester__request_notes"]'),
                ],
                'Catalog': [
                    ('instance_name', Input("service__vm_name")),
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

    def __init__(
            self, fields=None, tab_fields=None, identifying_loc=None, order=None, fields_end=None):
        fields = fields or list()
        if order is None:
            order = tab_fields.keys()
        else:
            order = list(order)
            if len(order) > len(tab_fields.keys()):
                raise ValueError("More order items passed than there is in real!")
            if len(order) < len(tab_fields.keys()):
                remaining_keys = set(tab_fields.keys()) - set(order)
                for key in remaining_keys:
                    order.append(key)
        for tab_ident in order:
            field = tab_fields[tab_ident]
            for field_name, field_locator in field:
                fields.append((field_name, _TabStripField(tab_ident, field_locator)))
        if fields_end is not None:
            fields.extend(fields_end)
        super(TabStripForm, self).__init__(fields, identifying_loc)
