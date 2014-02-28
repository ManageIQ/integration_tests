"""A set of functions for dealing with the paginator controls."""
import cfme.fixtures.pytest_selenium as sel
import re

_locator = '(//div[@id="paging_div"] | //div[@id="records_div"])'
_next = '//img[@alt="Next"]'
_previous = '//img[@alt="Previous"]'
_first = '//img[@alt="First"]'
_last = '//img[@alt="Last"]'
_num_results = '//select[@id="ppsetting" or @id="perpage_setting1"]'
_sort_by = '//select[@id="sort_choice"]'
_page_cell = '//td//td[contains(., " of ")]'
_check_all = '//input[@id="masterToggle"]'


def _page_nums():
    return sel.element(_locator + _page_cell).text


def check_all():
    """ Returns the Check All locator."""
    return sel.element(_locator + _check_all)


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
    select = sel.element(_locator + _num_results)
    sel.select(select, (sel.TEXT, str(num)))


def sort_by(sort):
    """ Changes the sort by field.

    Args:
        sort: Value to sort by (visible text in select box)
    """
    select = sel.element(_locator + _sort_by)
    sel.select(select, (sel.TEXT, sort))


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
    if 'dimmed' not in first().get_attribute('class'):
        sel.click(first())


def pages():
    """A generator to facilitate looping over pages

    Usage:

        for page in pages:
            # Do seleniumy things here, like finding and clicking elements

    """
    # Reset the paginator, then yield the first page
    reset()
    yield
    # Yield while there are more pages
    while 'dimmed' not in next().get_attribute('class'):
        sel.click(next())
        yield
