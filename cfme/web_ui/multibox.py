import re
from collections import Sequence, namedtuple

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Select, fill, flash
from utils.category import CategoryBase, categorize
from utils.log import logger
from utils.pretty import Pretty

SelectItem = namedtuple("SelectItem", ["sync", "value", "text"])


class Sync(CategoryBase):
    pass


class Async(CategoryBase):
    pass


class MultiBoxSelect(Pretty):
    """ Common UI element for selecting multiple items.

    Presence in eg. Control/Explorer/New Policy Profile (for selecting policies)

    Args:
        unselected: Locator for the left (unselected) list of items.
        selected: Locator for the right (selected) list of items.
        to_unselected: Locator for a button which moves items from right to left (unselecting)
        to_selected: Locator for a button which moves items from left to right (selecting)
        remove_all: If present, locator for a button which unselects all items (Default None)

    """
    pretty_attrs = ['unselected', 'selected']

    def __init__(self, unselected, selected, to_unselected, to_selected, remove_all=None,
                 sync=None, async=None):
        self._unselected = Select(unselected, multi=True)
        self._selected = Select(selected, multi=True)
        self._to_unselected = to_unselected
        self._to_selected = to_selected
        self._remove_all = remove_all
        if bool(sync) ^ bool(async):
            raise TypeError("You have to specify either both or none of (a)sync!")
        self._async = async
        self._sync = sync

    def __str__(self):
        return "{}({}, {})".format(
            type(self).__name__, str(self._unselected), str(self._selected))

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

    @property
    def all_selected(self):
        result = []
        for item in self._selected.options:
            sync = None
            desc = sel.text(item).encode("utf-8").lstrip()
            value = sel.get_attribute(item, "value")
            if self._sync:  # Or _async, this does not matter, protected in constructor
                # Extract
                sync_res, desc = re.match(r"^\(([AS])\) (.*?)$", desc).groups()
                sync = sync_res == "S"
            result.append(SelectItem(sync=sync, value=value, text=desc))
        return result

    def _set_sync_state(self, state, *values):
        assert self._async and self._sync, "You must set async= and sync=!"
        for value in values:
            self._clear_selection()
            try:
                self._unselected.select_by_visible_text(value)
                self._move_to_selected()
            except sel.NoSuchElementException:
                # Already selected
                pass
            try:
                item = filter(lambda i: i.text == value, self.all_selected)[0]
            except IndexError:
                raise NameError("Could not find {}!".format(value))
            if item.sync != state:
                self._clear_selection()
                self._selected.select_by_value(item.value)
                if state:
                    sel.click(self._sync)
                else:
                    sel.click(self._async)

    def set_sync(self, *values):
        return self._set_sync_state(True, *values)

    def set_async(self, *values):
        return self._set_sync_state(False, *values)

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

    @classmethod
    def categorize(cls, values, sync_l, async_l, dont_care_l):
        """Does categorization of values based on their Sync/Async status.

        Args:
            values: Values to be categorized.
            sync_l: List that will be used for appending the Sync values.
            async_l: List that will be used for appending the Async values.
            dont_care_l: List that will be used for appending all the other values.
        """
        categorize(values, {
            lambda item: isinstance(item, Async): lambda item: async_l.append(str(item)),
            lambda item: isinstance(item, Sync): lambda item: sync_l.append(str(item)),
            "default": lambda item: dont_care_l.append(str(item))
        })


@fill.method((MultiBoxSelect, Sequence))
def _fill_multibox_list(multi, values):
    """ Filler function for MultiBoxSelect

    Designed for `list` styled items, it flushes the selected list and then selects all items
    in provided list.

    Args:
        multi: :py:class:`MultiBoxSelect` to fill
        values: List with items to select

    Returns: :py:class:`bool` with success.
    """
    logger.debug('  Filling in %s with values %s', str(multi), str(values))
    if multi._async:
        sync = []
        async = []
        dont_care = []
        MultiBoxSelect.categorize(values, sync, async, dont_care)
        multi.add(*dont_care, flush=True)
        multi.set_async(*async)
        multi.set_sync(*sync)
    else:
        multi.add(*map(str, values), flush=True)


@fill.method((MultiBoxSelect, basestring))
def _fill_multibox_str(multi, string):
    """ Filler function for MultiBoxSelect

    Designed for `string`. Selects item with the name.

    Args:
        multi: :py:class:`MultiBoxSelect` to fill
        string: String to select

    Returns: :py:class:`bool` with success.
    """
    logger.debug('  Filling in %s with value %s', str(multi), string)
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
    enable_list, disable_list = [], []
    for key, value in d.iteritems():
        if value:
            enable_list.append(key)
        else:
            disable_list.append(key)
    logger.debug('  Disabling values %s in %s', str(disable_list), str(multi))
    logger.debug('  Enabling values %s in %s', str(enable_list), str(multi))
    multi.remove(*disable_list)
    if multi._async:
        sync, async, dont_care = [], [], []
        MultiBoxSelect.categorize(enable_list, sync, async, dont_care)
        multi.add(*dont_care)
        multi.set_async(*async)
        multi.set_sync(*sync)
    else:
        multi.add(*map(str, enable_list))
