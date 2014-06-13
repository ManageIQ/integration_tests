from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Select, fill, flash
from utils.log import logger


class MultiBoxSelect(object):
    """ Common UI element for selecting multiple items.

    Presence in eg. Control/Explorer/New Policy Profile (for selecting policies)

    Args:
        unselected: Locator for the left (unselected) list of items.
        selected: Locator for the right (selected) list of items.
        to_unselected: Locator for a button which moves items from right to left (unselecting)
        to_selected: Locator for a button which moves items from left to right (selecting)
        remove_all: If present, locator for a button which unselects all items (Default None)

    """
    def __init__(self, unselected, selected, to_unselected, to_selected, remove_all=None):
        self._unselected = Select(unselected, multi=True)
        self._selected = Select(selected, multi=True)
        self._to_unselected = to_unselected
        self._to_selected = to_selected
        self._remove_all = remove_all

    def _move_to_unselected(self):
        """ Clicks the button for moving items from selected to unselected.

        Returns: :py:class:`bool` with success.
        """
        sel.click(sel.element(self._to_unselected))
        return not any(map(flash.is_error, flash.get_all_messages()))

    def _move_to_selected(self):
        """ Clicks the button for moving items from unselected to selected.

        Returns: :py:class:`bool` with success.
        """
        sel.click(sel.element(self._to_selected))
        return not any(map(flash.is_error, flash.get_all_messages()))

    def _select_unselected(self, *items):
        """ Selects items in 'Unselected items' list

        Args:
            *items: Items to select
        """
        for item in items:
            sel.select(self._unselected, item)

    def _select_selected(self, *items):
        """ Selects items in 'Selected items' list

        Args:
            *items: Items to select
        """
        for item in items:
            sel.select(self._selected, item)

    def _clear_selection(self):
        """ Unselects all items in both lists to ensure unwanted items don't travel in between.
        """
        self._unselected.deselect_all()
        self._selected.deselect_all()

    def remove_all(self):
        """ Flush the list of selected items.

        Returns: :py:class:`bool` with success.
        """
        if len(self._selected.options) == 0:
            return  # No need to flush
        if self._remove_all is None:
            # Check all selected
            self.remove(*[sel.text(o).encode("utf-8").strip() for o in self._selected.options])
        else:
            sel.click(sel.element(self._remove_all))
        return not any(map(flash.is_error, flash.get_all_messages()))

    def add(self, *values, **kwargs):
        """ Mark items for selection and then clicks the button to select them.

        Args:
            *values: Values to select

        Keywords:
            flush: By using `flush` keyword, the selected items list is flushed prior to selecting
                new ones

        Returns: :py:class:`bool` with success.
        """
        if kwargs.get("flush", False):
            self.remove_all()
        self._clear_selection()
        self._select_unselected(*values)
        if len(self._unselected.all_selected_options) > 0:
            return self._move_to_selected()
        else:
            return True

    def remove(self, *values):
        """ Mark items for deselection and then clicks the button to deselect them.

        Args:
            *values: Values to deselect

        Returns: :py:class:`bool` with success.
        """
        self._clear_selection()
        self._select_selected(*values)
        if len(self._selected.all_selected_options) > 0:
            return self._move_to_unselected()
        else:
            return True

    @classmethod
    def default(cls):
        """ The most common type of the MultiBoxSelect

        Returns: :py:class:`MultiBoxSelect` instance
        """
        return cls(
            "//select[@id='choices_chosen']",
            "//select[@id='members_chosen']",
            "//a/img[contains(@alt, 'Remove selected')]",
            "//a/img[contains(@alt, 'Move selected')]",
            "//a/img[contains(@alt, 'Remove all')]",
        )


@fill.method((MultiBoxSelect, list))
@fill.method((MultiBoxSelect, tuple))
@fill.method((MultiBoxSelect, set))
def _fill_multibox_list(multi, values):
    """ Filler function for MultiBoxSelect

    Designed for `list` styled items, it flushes the selected list and then selects all items
    in provided list.

    Args:
        multi: :py:class:`MultiBoxSelect` to fill
        values: List with items to select

    Returns: :py:class:`bool` with success.
    """
    stype = type(multi)
    fill_values = tuple([str(value) for value in values])
    logger.debug('  Filling in %s with values %s' % (str(stype), str(fill_values)))
    return multi.add(*fill_values, flush=True)


@fill.method((MultiBoxSelect, basestring))
def _fill_multibox_str(multi, string):
    """ Filler function for MultiBoxSelect

    Designed for `string`. Selects item with the name.

    Args:
        multi: :py:class:`MultiBoxSelect` to fill
        string: String to select

    Returns: :py:class:`bool` with success.
    """
    stype = type(multi)
    logger.debug('  Filling in %s with value %s' % (str(stype), string))
    return multi.add(string)


@fill.method((MultiBoxSelect, dict))
def _fill_multibox_dict(multi, d):
    """ Filler function for MultiBoxSelect

    Designed for `dict` styled items. It expects a dictionary in format:
    >>> {"Some item": True, "Another item": False}
    Where key stands for the item name and value its selection status.
    Any items that have to be unselected will be unselected before selecting the unselected happens.

    Args:
        multi: :py:class:`MultiBoxSelect` to fill
        d: :py:class:`dict` with values.

    Returns: :py:class:`bool` with success.
    """
    stype = type(multi)
    enable_list, disable_list = [], []
    for key, value in d.iteritems():
        if value:
            enable_list.append(str(key))
        else:
            disable_list.append(str(key))
    logger.debug('  Disabling values %s in %s' % (str(disable_list), str(stype)))
    logger.debug('  Enabling values %s in %s' % (str(enable_list), str(stype)))
    return all((multi.remove(disable_list), multi.add(enable_list)))
