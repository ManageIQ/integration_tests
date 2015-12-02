"""A set of functions for dealing with the paginator controls."""
from cfme.web_ui import Select, Input, AngularSelect
import cfme.fixtures.pytest_selenium as sel
import re
from selenium.common.exceptions import NoSuchElementException
from functools import partial
from utils import version

_locator = '(//div[@id="paging_div"] | //div[@id="records_div"])'
_next = '//img[@alt="Next"]|//li[contains(@class, "next")]/span'
_previous = '//img[@alt="Previous"]|//li[contains(@class, "prev")]/span'
_first = '//img[@alt="First"]|//li[contains(@class, "first")]/span'
_last = '//img[@alt="Last"]|//li[contains(@class, "last")]/span'
_num_results = '//select[@id="ppsetting" or @id="perpage_setting1"]'
_sort_by = '//select[@id="sort_choice"]'
_page_cell = '//td//td[contains(., " of ")]|//li//span[contains(., " of ")]'
_check_all = Input("masterToggle")

_regexp = {version.LOWEST: r"(?:Item|Items)*\((?P<first>\d+)-(?P<last>\d+) of (?P<total>\d+)\)(?:item|items?)*",
           "5.5": r"Showing (?P<first>\d+)-(?P<last>\d+) of (?P<total>\d+) (?:item|items?)?"}


def page_controls_exist():
    """ Simple check to see if page controls exist. """
    return sel.is_displayed(_locator + _page_cell)


def _page_nums():
    return sel.text(_locator + _page_cell)


def check_all():
    """ Returns the Check All locator."""
    return sel.element(_locator + _check_all)


def is_dimmed(btn):
    tag = sel.tag(btn)
    if tag in {"li", "img"}:
        class_attr = sel.get_attribute(btn, "class")
    elif tag == "span":
        class_attr = sel.get_attribute(sel.element("..", root=btn), "class")
    else:
        raise TypeError("Wrong tag name {}".format(tag))
    class_att = set(re.split(r"\s+", class_attr))
    if {"dimmed", "disabled"}.intersection(class_att):
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
    _select = version.pick({
        "5.4": Select(_locator + _num_results),
        "5.5": AngularSelect('ppsetting')})
    sel.select(_select, sel.ByText(str(num)))


def sort_by(sort):
    """ Changes the sort by field.

    Args:
        sort: Value to sort by (visible text in select box)
    """
    _select = version.pick({
        "5.4": Select(_locator + _sort_by),
        "5.5": AngularSelect('sort_choice')})
    sel.select(_select, sel.ByText(str(sort)))


def _get_rec(partial):
    offset = re.search(version.pick(_regexp), _page_nums())
    if offset:
        return offset.groupdict()[partial]
    else:
        return None


def rec_offset():
    """ Returns the first record offset."""
    return _get_rec('first')


def rec_end():
    """ Returns the record set index."""
    return _get_rec('last')


def rec_total():
    """ Returns the total number of records."""
    return _get_rec('total')


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
