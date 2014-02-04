#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" The tab strip manipulation which appears in Configure / Configuration and possibly other pages.

Usage:

    import cfme.web_ui.tabstrip as tabs
    tabs.select_tab("Authentication")
    print is_tab_selected("Authentication")
    print get_selected_tab()

"""
import cfme.fixtures.pytest_selenium as sel


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
