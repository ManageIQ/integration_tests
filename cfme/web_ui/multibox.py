from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Select, fill, flash


class MultiBoxSelect(object):
    def __init__(self, unselected, selected, to_unselected, to_selected, remove_all=None):
        self._unselected = Select(unselected, multi=True)
        self._selected = Select(selected, multi=True)
        self._to_unselected = to_unselected
        self._to_selected = to_selected
        self._remove_all = remove_all

    def _move_to_unselected(self):
        sel.click(sel.element(self._to_unselected))
        return not any(map(flash.is_error, flash.get_all_messages()))

    def _move_to_selected(self):
        sel.click(sel.element(self._to_selected))
        return not any(map(flash.is_error, flash.get_all_messages()))

    def _select_unselected(self, *items):
        for item in items:
            sel.select(self._unselected, item)

    def _select_selected(self, *items):
        for item in items:
            sel.select(self._selected, item)

    def _clear_selection(self):
        self._unselected.deselect_all()
        self._selected.deselect_all()

    def remove_all(self):
        """ Flush the list of selected items.

        Returns: :py:class:`bool` with success.
        """
        if self._remove_all is None:
            raise NotImplementedError("'Remove all' button was not specified!")
        sel.click(sel.element(self._remove_all))
        return not any(map(flash.is_error, flash.get_all_messages()))

    def add(self, *values, **kwargs):
        """ Mark items for selection and then clicks the button to select them.

        Args:
            *values: Values to select

        Keywords:
            flush: By using `flush` keyword, the selected items list is flushed prior to selecting
                new ones
        Retuns: :py:class:`bool` with success.
        """
        if kwargs.get("flush", False):
            self.remove_all()
        self._clear_selection()
        self._select_unselected(*values)
        return self._move_to_selected()

    def remove(self, *values):
        """ Mark items for deselection and then clicks the button to deselect them.

        Args:
            *values: Values to deselect

        Returns: :py:class:`bool` with success.
        """
        self._clear_selection()
        self._select_selected(*values)
        return self._move_to_unselected()


@fill.method((MultiBoxSelect, list))
@fill.method((MultiBoxSelect, tuple))
@fill.method((MultiBoxSelect, set))
def _fill_multibox_list(multi, values):
    """ Filler function for MultiBoxSelect

    Returns: :py:class:`bool` with success.
    """
    return multi.add(*tuple(values), flush=True)


@fill.method((MultiBoxSelect, basestring))
def _fill_multibox_str(multi, string):
    """ Filler function for MultiBoxSelect

    Returns: :py:class:`bool` with success.
    """
    return multi.add(string)


@fill.method((MultiBoxSelect, dict))
def _fill_multibox_dict(multi, d):
    """ Filler function for MultiBoxSelect

    Returns: :py:class:`bool` with success.
    """
    enable_list, disable_list = [], []
    for key, value in d.iteritems():
        if value:
            enable_list.append(key)
        else:
            disable_list.append(key)
    return all((multi.remove(disable_list), multi.add(enable_list)))
