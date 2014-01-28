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


_locator = "//div[contains(@class, 'ui-tabs')]"  # Entry point


def _root():
    """ Returns the div element encapsulating whole tab strip as an entry point.

    Returns: WebElement
    """
    return sel.element(_locator)


def get_all_tabs():
    """ Return list of all tabs present.

    Returns: :py:class:`list` of :py:class:`str` Displayed names.
    """
    return [opt.text.strip().encode("utf-8") for opt in sel.elements("./ul/li/a", _root())]


def get_selected_tab():
    """ Return currently selected tab.

    Returns: :py:class:`str` Displayed name
    """
    return sel.element("./ul/li[@aria-selected='true']/a", _root())\
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
    return "true" in sel.element("..", element).get_attribute("aria-selected").lower()


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
    return sel.element("./ul/li/a[.='%s']" % ident_string, _root())


def select_tab(ident_string):
    """ Clicks on the tab with text from ident_string.

    Clicks only if it's not actually selected.

    Args:
        ident_string: The text displayed on the tab.

    """
    if not is_tab_selected(ident_string):
        return sel.click(get_clickable_tab(ident_string))
