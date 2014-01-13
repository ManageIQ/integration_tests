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
    def __init__(self, failed_clicks):
        self.failed_clicks = failed_clicks

    def __str__(self):
        return "Not all the required data elements were clicked [%s]" % ",".join(self.failed_clicks)
