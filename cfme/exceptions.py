# -*- coding: utf-8 -*-
"""Provides custom exceptions for the ``cfme`` module. """
import pytest
from cfme.utils.log import logger


class CFMEException(Exception):
    """Base class for exceptions in the CFME tree

    Used to easily catch errors of our own making, versus errors from external libraries.

    """
    pass


class BugException(CFMEException):
    """Raised by methods inside the framework that are broken due to a bug"""
    def __init__(self, bug_no, operation):
        self.bug_no = bug_no
        self.operation = operation

    def __str__(self):
        return "Bug {} blocks the operation [{}]".format(self.bug_no, self.operation)


class ConsoleNotSupported(CFMEException):
    """Raised by functions in :py:mod:`cfme.configure.configuration` when an invalid
    console type is given"""
    def __init__(self, product_name, version):
        self.product_name = product_name
        self.version = version

    def __str__(self):
        return "Console not supported on current version: {} {}".format(
            self.product_name,
            self.version
        )


class ConsoleTypeNotSupported(CFMEException):
    """Raised by functions in :py:mod:`cfme.configure.configuration` when an invalid
    console type is given"""
    def __init__(self, console_type):
        self.console_type = console_type

    def __str__(self):
        return "Console type not supported: {}".format(self.console_type)


class FlashMessageException(CFMEException):
    """Raised by functions in :py:mod:`cfme.web_ui.flash`"""

    def skip_and_log(self, message="Skipping due to flash message"):
        logger.error("Flash message error: %s", str(self))
        pytest.skip("{}: {}".format(message, str(self)))


class CFMEExceptionOccured(CFMEException):
    """Raised by :py:func:`cfme.web_ui.cfme_exception.assert_no_cfme_exception` when there is
    a Rails exception currently on page."""
    pass


class ToolbarOptionGreyedOrUnavailable(CFMEException):
    """Raised when toolbar wants to click item that is greyed or unavailable"""
    pass


class AddProviderError(CFMEException):
    pass


class AuthModeUnknown(CFMEException):
    """
    Raised if an invalid authenctication mode is passed to
    :py:func:`cfme.configure.configuration.set_auth_mode`
    """
    pass


class AutomateImportError(CFMEException):
    """Raised by scripts dealing with Automate when importing automate XML fails"""
    pass


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
    def __init__(self, d):
        self.d = d

    @property
    def message(self):
        return ", ".join("{}: {}".format(k, v) for k, v in self.d.iteritems())

    def __str__(self):
        return self.message


class TreeNotFound(CFMEException):
    """
    Raised if the tree used for  :py:meth:`cfme.web_ui.Tree.expand_path` cannot be found
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
        return 'Unable to navigate to page "{}"'.format(self.page_name)
    pass


class CannotContinueWithNavigation(CFMEException):
    """Used when it is not possible to continue with navigation.

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
        return "Not all the required data elements were clicked [{}]".format(
            ",".join(self.failed_clicks))


class NotAllCheckboxesFound(CFMEException):
    """
    Raised if not all the checkboxes could be found during e.g.
    :py:meth:`cfme.web_ui.CheckboxTable.select_rows` and other methods of this class.
    """
    def __init__(self, failed_selects):
        self.failed_selects = failed_selects

    def __str__(self):
        return "Not all the required data elements were selected/deselected [{}]".format(
            ",".join(self.failed_selects))


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
    pass


class RequestException(CFMEException):
    """
    Raised if a request was not found or multiple rows matched during _request functions in
    :py:mod:`cfme.services.requests`
    """
    pass


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


class VmNotFoundViaIP(CFMEException):
    """
    Raised if a specific VM cannot be found.
    """
    pass


class VmOrInstanceNotFound(CFMEException):
    pass


class VmNotFound(VmOrInstanceNotFound):
    """
    Raised if a specific VM cannot be found.
    """
    pass


class InstanceNotFound(VmOrInstanceNotFound):
    """
    Raised if a specific instance cannot be found.
    """
    pass


class ImageNotFound(VmOrInstanceNotFound):
    """
    Raised if a specific image cannot be found
    """
    pass


class TenantNotFound(CFMEException):
    """
        Raised if a specific tenant cannot be found
        """
    pass


class TemplateNotFound(CFMEException):
    """
    Raised if a specific Template cannot be found.
    """
    pass


class ClusterNotFound(CFMEException):
    """Raised if a cluster is not found"""
    pass


class HostNotFound(CFMEException):
    """Raised if a specific host cannot be found in UI."""
    pass


class NodeNotFound(CFMEException):
    """Raised if a specific container node cannot be found in the UI"""
    pass


class StackNotFound(CFMEException):
    """
    Raised if a specific stack cannot be found.
    """
    pass


class FlavorNotFound(CFMEException):
    """
    Raised if a specific cloud flavor cannot be found in the UI
    """
    pass


class KeyPairNotFound(CFMEException):
    """
    Raised if a specific cloud key pair cannot be found in the UI
    """
    pass


class ResourcePoolNotFound(CFMEException):
    """
    Raised if a specific cloud key pair cannot be found in the UI
    """
    pass


class AvailabilityZoneNotFound(CFMEException):
    """
    Raised if a specific Cloud Availability Zone cannot be found.
    """
    pass


class VolumeNotFound(CFMEException):
    """
    Raised if a specific cloud volume cannot be found in the UI
    """
    pass


class OptionNotAvailable(CFMEException):
    """
    Raised if a specified option is not available.
    """
    pass


class ListAccordionLinkNotFound(CFMEException):
    """
    Raised when active link containing specific text could not be found in
    expended :py:mod:`cfme.web_ui.listaccordion` content section.
    """
    pass


class ZoneNotFound(CFMEException):
    """
    Raised when a specific Zone cannot be found in the method
    :py:mod:`cfme.configure.configuration`.
    """
    pass


class UnknownProviderType(CFMEException):
    """
    Raised when the passed provider or provider type is not known or usable in given context
    e.g. when getting a provider from yaml and the provider type doesn't match any of known types
    or when an infra provider is passed to the cloud's instance_factory method
    """
    pass


class AccordionItemNotFound(CFMEException):
    """Raised when it's not possible to locate and accordion item."""


class CannotScrollException(CFMEException):
    """Raised when even during the heaviest workarounds for scrolling failure comes."""


class StorageManagerNotFound(CFMEException):
    """Raised when a Storage Manager is not found"""
    pass


class CUCommandException(CFMEException):
    """Raised when one of the commands run to set up a CU VM fails """
    pass


class PaginatorException(CFMEException):
    """Raised by functions in :py:mod:`cfme.web_ui.paginator`"""

    pass


class MiddlewareProviderNotFound(CFMEException):
    """
    Raised if a specific Middleware Provider cannot be found.
    """
    pass


class MiddlewareServerNotFound(CFMEException):
    """
    Raised if a specific Middleware Server cannot be found.
    """
    pass


class MiddlewareServerGroupNotFound(CFMEException):
    """
    Raised if a specific Middleware Server Group cannot be found.
    """
    pass


class MiddlewareDomainNotFound(CFMEException):
    """
    Raised if a specific Middleware Domain cannot be found.
    """
    pass


class MiddlewareDatasourceNotFound(CFMEException):
    """
    Raised if a specific Middleware Datasource cannot be found.
    """
    pass


class MiddlewareDeploymentNotFound(CFMEException):
    """
    Raised if a specific Middleware Deployment cannot be found.
    """
    pass


class MiddlewareMessagingNotFound(CFMEException):
    """
    Raised if a specific Middleware Messaging cannot be found.
    """
    pass


class JDBCDriverConfigNotFound(CFMEException):
    """Raised when cdme_data.yaml file does not contain configuration of 'jdbc_drivers'."""


class DbAllocatorConfigNotFound(CFMEException):
    """Raised when cdme_data.yaml file does not contain configuration of 'db_allocator'."""


class LabelNotFoundException(Exception):
    "Raises when failed to remove label from object via cli"
    pass


class UsingSharedTables(CFMEException):
    """Raised if the :py:class:`cfme.web_ui.Table` suspects there is a use of shared tables."""


class MenuItemNotFound(CFMEException):
    """Raised during navigation of certain menu item was not found."""


class DestinationNotFound(CFMEException):
    """Raised during navigation where the navigator destination is not found"""


class ItemNotFound(CFMEException):
    """Raised when an item is not found in general."""


class ManyEntitiesFound(CFMEException):
    """Raised when one or no items were expected but several/many items were obtained instead."""


class RoleNotFound(CFMEException):
    """Raised when Deployment role not found"""


class RBACOperationBlocked(CFMEException):
    """
    Raised when a Role Based Access Control operation is blocked from execution due to invalid
    permissions. Also thrown when trying to perform actions CRUD operations on roles/groups/users
    that are CFME defaults
    """
