"""Provides custom exceptions for the ``cfme`` module. """


class CFMEException(Exception):
    """Base class for exceptions in the CFME tree

    Used to easily catch errors of our own making, versus errors from external libraries.

    """
    pass


class CFMEExceptionOccured(CFMEException):
    """Raised by :py:func:`cfme.web_ui.cfme_exception.assert_no_cfme_exception` when there is
    a Rails exception currently on page."""
    pass


class AddProviderError(CFMEException):
    pass


class AuthModeUnknown(CFMEException):
    """
    Raised if an invalid authenctication mode is passed to
    :py:func:`cfme.configure.configuration.set_auth_mode`
    """


class BlockTypeUnknown(CFMEException):
    """
    Raised if the block type requested to :py:class:`cfme.web_ui.InfoBlock`.
    """
    pass


class CandidateNotFound(CFMEException):
    """
    Raised if there is no candidate found whilst trying to traverse a tree in
    :py:meth:`cfme.web_ui.Tree.click_path`.
    """
    pass


class ElementOrBlockNotFound(CFMEException):
    """
    Raised if an Element or a Block is not found whilst locating in
    :py:meth:`cfme.web_ui.InfoBlock`.
    """
    pass


class HostStatsNotContains(CFMEException):
    """
    Raised if the hosts information does not contain the specified key whilst running
    :py:meth:`cfme.cloud.provider.Provider.do_stats_match`.
    """
    pass


class NavigationError(CFMEException):
    """Raised when the pytest.sel.go_to function is unable to navigate to the requested page."""
    def __init__(self, page_name):
        self.page_name = page_name

    def __str__(self):
        return 'Unable to navigate to page "%s"' % self.page_name
    pass


class CannotContinueWithNavigation(CFMEException):
    """Used for telling force_navigate that is not possible to continue with navigation.

    Raising it will recycle the browser, therefore refresh the session. If you pass a string to
    the constructor, it will be written to the log.
    """
    pass


class NoElementsInsideValue(CFMEException):
    """
    Raised if the value part of key/value contains no elements during
    :py:meth:`cfme.web_ui.InfoBlock.get_el_or_els`.
    """
    pass


class NotAllItemsClicked(CFMEException):
    """
    Raised if not all the items could be clicked during :py:meth:`cfme.web_ui.Table.click_cell`.
    """
    def __init__(self, failed_clicks):
        self.failed_clicks = failed_clicks

    def __str__(self):
        return "Not all the required data elements were clicked [%s]" % ",".join(self.failed_clicks)


class NotAllCheckboxesFound(CFMEException):
    """
    Raised if not all the checkboxes could be found during e.g.
    :py:meth:`cfme.web_ui.CheckboxTable.select_rows` and other methods of this class.
    """
    def __init__(self, failed_selects):
        self.failed_selects = failed_selects

    def __str__(self):
        return "Not all the required data elements were selected/deselected [%s]" % ","\
               .join(self.failed_selects)


class ProviderHasNoKey(CFMEException):
    """
    Raised if the :py:meth:`cfme.cloud.provider.Provider.get_mgmt_system` method is called
    but the Provider instance has no key.
    """
    pass


class ProviderHasNoProperty(CFMEException):
    """
    Raised if the provider does not have the property requested whilst running
    :py:meth:`cfme.cloud.provider.Provider.do_stats_match`.
    """
    pass


class ScheduleNotFound(CFMEException):
    """
    Raised if a schedule was not found in
    :py:meth:`cfme.configure.configuration.Schedule.delete_by_name`
    """


class RequestNotFound(CFMEException):
    """
    Raised if a request was not found during _request functions in
    :py:mod:`cfme.services.requests`
    """


class TreeTypeUnknown(CFMEException):
    """
    Raised if the tree type is known whilst detection in :py:class:`cfme.web_ui.Tree`
    """
    pass


class UnidentifiableTagType(CFMEException):
    """
    Raised if a tag type is not identifiable when processing a form in
    :py:meth:`cfme.web_ui.Form.fill_fields`.
    """
    pass


class NoVmFound(CFMEException):
    """
    Raised if a specific VM cannot be found.
    """
    pass


class HostNotFound(CFMEException):
    """Raised if a specific host cannot be found in UI."""
    pass


class NoOptionAvailable(CFMEException):
    """
    Raised if required option is not specified.
    """
    pass


class ParmRequired(CFMEException):
    """
    Raised if a required parameter is not passed to a particular method.
    """
    pass


class ParmConfusion(CFMEException):
    """
    Raised when two exclusive function parameters for a particular method are passed in
    at the same time.
    """
    pass


class FormButtonNotFound(CFMEException):
    """Raised when ::py:func:`cfme.web_ui.form_buttons._get_button_element` function cannot
    find provided button by its title."""
    pass
