"""A set of functions for dealing with the paginator controls."""
from widgetastic_manageiq import PaginationPane
from cfme.utils.appliance import get_or_create_current_appliance


def new_paginator():
    """ Simple function to avoid module level import """
    appliance = get_or_create_current_appliance()
    paginator = PaginationPane(parent=appliance.browser.widgetastic)
    return paginator


def page_controls_exist():
    """ Simple check to see if page controls exist. """
    return new_paginator().is_displayed


def check_all():
    """ selects all items """
    new_paginator().check_all()


def uncheck_all():
    """ unselects all items """
    new_paginator().uncheck_all()


def next():
    """ Returns the Next button locator."""
    new_paginator().next_page()


def previous():
    """ Returns the Previous button locator."""
    new_paginator().prev_page()


def first():
    """ Returns the First button locator."""
    new_paginator().first_page()


def last():
    """ Returns the Last button locator."""
    new_paginator().last_page()


def sort_by(sort):
    """ Changes the sort by field.

    Args:
        sort: Value to sort by (visible text in select box)
    """
    new_paginator().sort(sort)


def rec_total():
    """ Returns the total number of records."""
    return new_paginator().items_amount


def pages():
    """A generator to facilitate looping over pages

    Usage:

        for page in pages():
            # Do seleniumy things here, like finding and clicking elements

    Raises:
        :py:class:`ValueError`: When the paginator "breaks" (does not change)
    """
    return new_paginator().pages()


def reset_selection():
    new_paginator().reset_selection()
