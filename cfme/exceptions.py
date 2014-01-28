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
    Raised if not all the items could be clicked during :py:meth:`cfme.web_ui.Table.click_cell`.
    """
    def __init__(self, failed_clicks):
        self.failed_clicks = failed_clicks

    def __str__(self):
        return "Not all the required data elements were clicked [%s]" % ",".join(self.failed_clicks)


class AddProviderError(Exception):
    pass


class CandidateNotFound(Exception):
    """
    Raised if there is no candidate found whilst trying to traverse a tree in
    :py:meth:`cfme.web_ui.Tree.click_path`
    """
    pass


class TreeTypeUnknown(Exception):
    """
    Raised if the tree type is known whilst detection in :py:class:`cfme.web_ui.Tree`
    """
    pass


class BlockTypeUnknown(Exception):
    """
    Raised if the block type requested to :py:class:`cfme.web_ui.InfoBlock`
    """
    pass


class ElementOrBlockNotFound(Exception):
    """
    Raised if an Element or a Block is not found whilst locating in
    :py:meth:`cfme.web_ui.InfoBlock`.
    """
    pass


class NoElementsInsideValue(Exception):
    """
    Raised if the value part of key/value contains no elements during
    :py:meth:`cfme.web_ui.InfoBlock.get_el_or_els`
    """
    pass
