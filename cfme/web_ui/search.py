# -*- coding: utf-8 -*-
"""This module operates the `Advanced search` box located on multiple pages."""
import re
from functools import partial

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import expression_editor as exp_ed
from cfme.web_ui import Input, Region, Select, fill
from cfme.web_ui.form_buttons import FormButton
from utils.wait import wait_for
from utils.log import logger

search_box = Region(
    locators=dict(
        # Filter of results, the search field that is normally visible
        search_field=Input("search_text", "search[text]"),

        # The icon buttons for searching
        search_icon={
            "5.4":
            "//div[@id='searchbox']//div[contains(@class, 'form-group')]"
            "/*[self::a or (self::button and @type='submit')]"},

        # The arrow opening/closing the advanced search box
        toggle_advanced="(//button | //a)[@id='adv_search']",

        # Container for the advanced search box
        # class changes when visible or hidden, first locator does not indicate visibility
        advanced_search_box="//div[@id='advsearchModal']//div[@class='modal-content']",
        advanced_search_box_visible="//div[@id='advsearchModal' and @class='modal fade in']"
                                    "//div[@class='modal-content']",

        # Alt text is missing for some buttons, locators where FormButton won't work
        # https://bugzilla.redhat.com/show_bug.cgi?id=1380430
        # Can remove locators when alt-text is consistent, and use FormButtons
        load_filter='//button[(normalize-space(@alt)="Load a filter")]',
        load_filter_disabled='//button[(normalize-space(@alt)="No saved filters or report '
                                    'filters are available to load")]',

        reset_filter='//a[@title="Reset the filter"]',
        reset_filter_disabled='//button[contains(@class, "btn-disabled") and '
                              'normalize-space(text())="Reset"]',

        apply_filter='//a[@title="Apply the filter"]',
        apply_filter_disabled='//button[contains(@class, "btn-disabled") and '
                              'normalize-space(text())="Apply"]',


        # Buttons on main view
        # https://bugzilla.redhat.com/show_bug.cgi?id=1380430
        # TODO: update dimmed/disabled alt-text as 1380430 is fixed
        apply_filter_button=FormButton("Apply the current filter"),
        load_filter_button=FormButton(alt="Load a filter",
                                      dimmed_alt="No saved filters or report filters are "
                                                 "available to load"),
        delete_filter_button=FormButton("Delete the filter named", partial_alt=True),
        save_filter_button=FormButton("Save the current filter"),
        reset_filter_button=FormButton("Reset the filter"),
        # There are multiple close button divs, and they swap visibility with @style none/block
        close_button="//div[(@id='advsearchModal' or 'quicksearchbox') "
                     "and (normalize-space(@style)='display: block;')]//button[@class='close']"
                     "/span[normalize-space(.)='×']",

        # Buttons in the "next step"
        load_filter_dialog_button=FormButton("Load the filter shown above"),
        cancel_load_filter_dialog_button=FormButton("Cancel the load"),
        save_filter_dialog_button=FormButton("Save the current search"),
        cancel_save_filter_dialog_button=FormButton("Cancel the save"),

        # If user input requested, this window appears
        quick_search_box="//div[@id='quicksearchbox']",

        # With these buttons
        userinput_apply_filter_button=FormButton("Apply the current filter (Enter)"),
        userinput_cancel_button=FormButton("Cancel (Esc)"),

        # Elements in Load dialog
        # Selects for selecting the filter
        saved_filter=Select("select#chosen_search"),
        report_filter=Select("select#chosen_report"),

        # Elements in Save dialog
        save_name=Input("search_name"),
        global_search=Input("search_type"),

        # On the main page, this link clears the filters
        clear_advanced_search="//a[contains(@href, 'adv_search_clear')]",
    )
)


def _answering_function(answers_dict, text, element):
    """A generic answering function for filling user-input elements

    Args:
        answers_dict: Dictionary with answers. Keys are patterns matched in `text`. If it is string,
            python's `in` operator is used. If it is an object produced by :py:func:`re.compile`,
            then it is matched using its `.match()` method. If matched, element is filled with the
            dict-key's value.
        text: Text that is provided by :py:func:`_process_user_filling`.
        element: Element that is provided by :py:func:`_process_user_filling`.
    """
    for answer_key, answer_value in answers_dict.iteritems():
        if isinstance(answer_key, re._pattern_type):
            if answer_key.match(text) is not None:
                fill(element, str(answer_value))
                return True
        else:
            if answer_key in text:
                fill(element, str(answer_value))
                return True
    else:
        return False


def has_quick_search_box():
    return sel.is_displayed(search_box.quick_search_box)


def is_advanced_search_opened():
    """Checks whether the advanced search box is currently opened"""
    # Covers advanced search sub-forms as well - user-input, load, and save
    return any(sel.is_displayed(loc) for loc in
               [search_box.advanced_search_box_visible,
                search_box.quick_search_box,
                search_box.saved_filter,
                search_box.save_name])


def is_advanced_search_possible():
    """Checks for advanced search possibility in the quadicon view"""
    return sel.is_displayed(search_box.toggle_advanced)


def is_advanced_filter_applied():
    """Checks whether any filter is in effect on quadicon view"""
    ensure_advanced_search_closed()
    return len(filter(sel.is_displayed, sel.elements(search_box.clear_advanced_search))) > 0


def ensure_no_filter_applied():
    """If any filter is applied in the quadicon view, it will be disabled."""
    # The expression filter
    if is_advanced_filter_applied():
        logger.debug('search.ensure_no_filter_applied: advanced filter applied, removing')
        # Clear filter using breadcrumb link
        ensure_advanced_search_closed()
        sel.click(search_box.clear_advanced_search)

    # The simple filter
    if len(sel.value(search_box.search_field).strip()) > 0:
        logger.debug('search.ensure_no_filter_applied: simple filter applied, removing')
        sel.set_text(search_box.search_field, "")
        sel.click(search_box.search_icon)

    reset_filter()


def check_and_click_open():
    """Check for display of advanced search open button and click it"""
    # Look for close button since it overlays the toggle button
    if not sel.is_displayed(search_box.close_button):
        logger.debug('search.check_and_click_open: clicking advanced search toggle')
        sel.click(search_box.toggle_advanced)


def check_and_click_close():
    """Check for display of advanced search close button and click it"""
    if sel.is_displayed(search_box.close_button):
        logger.debug('search.check_and_click_close: clicking advanced search close')
        sel.click(search_box.close_button)


def ensure_advanced_search_open():
    """Make sure the advanced search box is opened.

    If the advanced search box is closed, open it if it exists (otherwise exception raised).
    """
    if not is_advanced_search_possible():
        raise Exception("Advanced search is not possible in this location!")
    if not is_advanced_search_opened():
        logger.debug('search.ensure_advanced_search_closed: search was closed, opening')
        sel.click(search_box.toggle_advanced)   # Open

    wait_for(is_advanced_search_opened, fail_condition=False, num_sec=10, delay=2,
             fail_func=check_and_click_open, message='Waiting for advanced search to open')


def ensure_advanced_search_closed():
    """Checks if the advanced search box is open and if it does, closes it."""
    if is_advanced_search_opened():
        logger.debug('search.ensure_advanced_search_closed: search was open, closing')
        sel.click(search_box.close_button)
        wait_for(is_advanced_search_opened, fail_condition=True, num_sec=10, delay=2,
                 fail_func=check_and_click_close, message='Waiting for advanced search to close')


def reset_filter():
    """Clears the filter expression"""
    ensure_advanced_search_open()
    if sel.is_displayed(search_box.reset_filter):
        return sel.click(search_box.reset_filter_button)
    else:
        return False


def apply_filter():
    """Applies an existing filter"""
    ensure_advanced_search_open()
    if sel.is_displayed(search_box.apply_filter):
        return sel.click(search_box.apply_filter_button)
    else:
        return False


def delete_filter(cancel=False):
    """If possible, deletes the currently loaded filter."""
    ensure_advanced_search_open()
    if sel.is_displayed(search_box.delete_filter_button):
        sel.click(search_box.delete_filter_button, wait_ajax=False)
        sel.handle_alert(cancel)
        return True
    else:
        return False


def normal_search(search_term):
    """Do normal search via the search bar.

    Args:
        search_term: What to search.
    """
    ensure_advanced_search_closed()
    fill(search_box.search_field, search_term)
    sel.click(search_box.search_icon)


def ensure_normal_search_empty():
    """Makes sure that the normal search field is empty."""
    normal_search('')


def fill_expression(expression_program):
    """Wrapper to open the box and fill the expression

    Args:
        expression_program: the expression to be filled.
    """
    ensure_advanced_search_open()
    exp_ed.create_program(expression_program)()  # Run the expression editing


def save_filter(expression_program, save_name, global_search=False, cancel=False):
    """Fill the filtering expression and save it

    Args:
        expression_program: the expression to be filled.
        save_name: Name of the filter to be saved with.
        global_search: Whether to check the Global search checkbox.
        cancel: Whether to cancel the save dialog without saving
    """
    fill_expression(expression_program)
    sel.click(search_box.save_filter_button)
    fill(search_box.save_name, save_name)
    fill(search_box.global_search, global_search)
    button = search_box.cancel_save_filter_dialog_button if cancel \
        else search_box.save_filter_dialog_button

    return sel.click(button)


def load_filter(saved_filter=None, report_filter=None, cancel=False):
    """Load saved filter

    Args:
        saved_filter: `Choose a saved XYZ filter`
        report_filter: `Choose a XYZ report filter`
        cancel: Whether to cancel the load dialog without loading
    """
    ensure_advanced_search_open()
    if sel.is_displayed(search_box.load_filter_disabled):
        raise DisabledButtonException('Load Filter button disabled, '
            'cannot load filter: {}'.format(saved_filter))
    assert saved_filter is not None or report_filter is not None, "At least 1 param required!"
    assert (saved_filter is not None) ^ (report_filter is not None), "You must provide just one!"

    sel.click(search_box.load_filter_button)
    # We apply it to the whole form but it will fill only one of the selects
    if saved_filter is not None:
        fill(search_box.saved_filter, saved_filter)
    else:   # No other check needed, covered by those two asserts
        fill(search_box.report_filter, report_filter)
    button = search_box.cancel_load_filter_dialog_button if cancel \
        else search_box.load_filter_dialog_button

    return sel.click(button)
    # todo update flash message handler


def _process_user_filling(fill_callback, cancel_on_user_filling=False):
    """This function handles answering CFME's requests on user input.

    A `fill_callback` function is passed. If the box with user input appears, all requested
    inputs are gathered and iterated over. On each element the `fill_callback` function is called
    with 2 parameters: text which precedes the element itself to do matching, and the element.

    This function does not check return status after `fill_callback` call.

    Args:
        fill_callback: The function to be called on each user input.
    """
    if has_quick_search_box():  # That is the one with user inputs
        if fill_callback is None:
            raise Exception("User should have provided a callback function!")
        if isinstance(fill_callback, dict):
            fill_callback = partial(_answering_function, fill_callback)
        for input in sel.elements(
                {
                    "5.4": "//div[@id='user_input_filter']//*[contains(@id, 'value_')]"
                },
                root=sel.element(search_box.quick_search_box)):
            fill_callback(  # Let the func fill it
                sel.text(input.find_element_by_xpath("..")),    # Parent element's text
                input  # The form element
            )
        if cancel_on_user_filling:
            sel.click(search_box.userinput_cancel_button)
        else:
            sel.click(search_box.userinput_apply_filter_button)


def load_and_apply_filter(
        saved_filter=None, report_filter=None, fill_callback=None, cancel_on_user_filling=False):
    """Load the filtering expression and apply it

    Args:
        saved_filter: `Choose a saved XYZ filter`.
        report_filter: `Choose a XYZ report filter`.
        fill_callback: Function to be called for each asked user input.
    """
    ensure_advanced_search_closed()
    ensure_no_filter_applied()
    load_filter(saved_filter, report_filter)
    sel.click(search_box.apply_filter_button)
    _process_user_filling(fill_callback, cancel_on_user_filling)
    ensure_advanced_search_closed()


def fill_and_apply_filter(expression_program, fill_callback=None, cancel_on_user_filling=False):
    """Fill the filtering expression and apply it

    Args:
        expression_program: Expression to fill to the filter.
        fill_callback: Function to be called for each asked user input
            (:py:func:`_process_user_filling`).
    """
    ensure_advanced_search_closed()
    ensure_no_filter_applied()
    fill_expression(expression_program)
    sel.click(search_box.apply_filter_button)
    _process_user_filling(fill_callback, cancel_on_user_filling)
    ensure_advanced_search_closed()


def save_and_apply_filter(expression_program, save_name, global_search=False):
    save_filter(expression_program=expression_program, save_name=save_name,
            global_search=global_search)
    apply_filter()
    ensure_advanced_search_closed()


class DisabledButtonException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
