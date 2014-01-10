"""
cfme.exceptions
---------------

The :py:mod:`cfme.exceptions` module provides custom exceptions for the ``cfme`` module.
"""


class UnidentifiableTagType(Exception):
    """
    Raised if a tag type is not identifiable when processing a form in
    :py:meth:`cfme.web_ui.Form.fill_fields`.
    """
    pass


class NotAllItemsClicked(Exception):
    """
    Raised if not all the items could be clicked during :py:meth:`cfme.web_ui.Table.click_item`.
    """
    pass
