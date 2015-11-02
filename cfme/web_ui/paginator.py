"""A set of functions for dealing with the paginator controls."""
from cfme.web_ui import Select, Input, AngularSelect
import cfme.fixtures.pytest_selenium as sel
import re
from selenium.common.exceptions import NoSuchElementException
from functools import partial
from utils import version

_locator = '(//div[@id="paging_div"] | //div[@id="records_div"])'
_next = '//img[@alt="Next"]|//li[contains(@class, "next")]'
_previous = '//img[@alt="Previous"]|//li[contains(@class, "prev")]'
_first = '//img[@alt="First"]|//li[contains(@class, "first")]'
_last = '//img[@alt="Last"]|//li[contains(@class, "last")]'
_num_results = '//select[@id="ppsetting" or @id="perpage_setting1"]'
_sort_by = '//select[@id="sort_choice"]'
_page_cell = '//td//td[contains(., " of ")]|//li//span[contains(., " of ")]'
_check_all = Input("masterToggle")


def page_controls_exist():
    """ Simple check to see if page controls exist. """
    return sel.is_displayed(_locator + _page_cell)


def _page_nums():
    return sel.element(_locator + _page_cell).text


def check_all():
    """ Returns the Check All locator."""
    return sel.element(_locator + _check_all)


def is_dimmed(btn):
    class_att = btn.get_attribute('class').split(" ")
    if {"dimmed", "disabled"}.intersection(set(class_att)):
        return True


def next():
    """ Returns the Next button locator."""
    btn = sel.element(_locator + _next)
    return btn


def previous():
    """ Returns the Previous button locator."""
    btn = sel.element(_locator + _previous)
    return btn


def first():
    """ Returns the First button locator."""
    btn = sel.element(_locator + _first)
    return btn


def last():
    """ Returns the Last button locator."""
    btn = sel.element(_locator + _last)
    return btn


def results_per_page(num):
    """ Changes the number of results on a page.

    Args:
        num: Number of results per page
    """
    if version.current_version() > '5.5.0.7':
        select = AngularSelect('ppsetting')
        sel.select(select, sel.ByText(str(num)))
    else:
        select = sel.element(_locator + _num_results)
        sel.select(Select(select), sel.ByText(str(num)))


def sort_by(sort):
    """ Changes the sort by field.

    Args:
        sort: Value to sort by (visible text in select box)
    """
    if version.current_version() > '5.5.0.7':
        select = AngularSelect('sort_choice')
        sel.select(select, sel.ByText(str(sort)))
    else:
        select = sel.element(_locator + _sort_by)
        sel.select(Select(select), sel.ByText(sort))


def rec_offset():
    """ Returns the first record offset."""
    offset = re.search('\((Item|Items)*\s*(\d+)', _page_nums())
    return offset.groups()[1]


def rec_end():
    """ Returns the record set index."""
    offset = re.search('-(\d+)', _page_nums())
    if offset:
        return offset.groups()[0]
    else:
        return rec_total()


def rec_total():
    """ Returns the total number of records."""
    offset = re.search('(\d+)\)', _page_nums())
    if offset:
        return offset.groups()[0]
    else:
        return None


def reset():
    """Reset the paginator to the first page or do nothing if no pages"""
    if not is_dimmed(first()):
        sel.click(first())


def pages():
    """A generator to facilitate looping over pages

    Usage:

        for page in pages():
            # Do seleniumy things here, like finding and clicking elements

    """
    # Reset the paginator, then yield the first page
    if page_controls_exist():
        reset()
        yield
        # Yield while there are more pages
        while not is_dimmed(next()):
            sel.click(next())
            yield
    else:
        yield


def find(pred):
    """Advance the pages until pred (a no-arg function) is true."""
    for page in pages():
        if pred():
            break
    else:
        raise NoSuchElementException


def find_element(el):
    """Advance the pages until the given element is displayed"""
    find(partial(sel.is_displayed, el))


def click_element(el):
    """Advance the page until the given element is displayed, and click it"""
    find_element(el)
    sel.click(el)
