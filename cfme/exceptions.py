"""Provides custom exceptions for the ``cfme`` module. """


class CFMEException(Exception):
    """Base class for exceptions in the CFME tree

    Used to easily catch errors of our own making, versus errors from external libraries.

    """
    pass


class ApplianceVersionException(CFMEException):
    """Raised when functionality is not supported on this version of the appliance"""
    def __init__(self, msg, version):
        self.msg = msg
        self.version = version

    def __str__(self):
        return "Version {} not supported.  {}".format(self.version, self.msg)


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


class TaskFailedException(CFMEException):
    """Raised by functions in :py:mod:`cfme/configure/tasks` when task is finished
    with some error message"""
    def __init__(self, task_name, message):
        self.task_name = task_name
        self.message = message

    def __str__(self):
        return "Task {} error: {}".format(self.task_name, self.message)


class CFMEExceptionOccured(CFMEException):
    """Raised by when there is a Rails exception currently on page."""
    pass


class ToolbarOptionGreyedOrUnavailable(CFMEException):
    """Raised when toolbar wants to click item that is greyed or unavailable"""
    pass


class AddProviderError(CFMEException):
    pass


class AuthModeUnknown(CFMEException):
    """
    Raised if an invalid authenctication mode is passed to
    :py:func:`cfme.configure.configuration.ServerAuthentication.configure_auth`
    """
    pass


class AutomateImportError(CFMEException):
    """Raised by scripts dealing with Automate when importing automate XML fails"""
    pass


class CandidateNotFound(CFMEException):
    """
    Raised if there is no candidate found whilst trying to traverse a tree
    """
    def __init__(self, d):
        self.d = d

    @property
    def message(self):
        return ", ".join("{}: {}".format(k, v) for k, v in self.d.items())

    def __str__(self):
        return self.message


class HostStatsNotContains(CFMEException):
    """
    Raised if the hosts information does not contain the specified key whilst running
    :py:meth:`cfme.cloud.provider.Provider.do_stats_match`.
    """
    pass


class RackStatsDoesNotContain(CFMEException):
    """
    Raised if the rack information does not contain the specified key whilst running
    :py:meth:`cfme.cloud.provider.Provider.do_stats_match`.
    """
    pass


class ChassisStatsDoesNotContain(CFMEException):
    """
    Raised if the chassis information does not contain the specified key whilst running
    :py:meth:`cfme.cloud.provider.Provider.do_stats_match`.
    """
    pass


class NavigationError(CFMEException):
    """Raised when pytest_selenium.go_to function is unable to navigate to the requested page."""
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


class ProviderHasNoKey(CFMEException):
    """
    Raised if the :py:meth:`cfme.cloud.provider.Provider.mgmt` method is called
    but the Provider instance has no key.
    """
    pass


class ProviderHasNoProperty(CFMEException):
    """
    Raised if the provider does not have the property requested whilst running
    :py:meth:`cfme.cloud.provider.Provider.do_stats_match`.
    """
    pass


class RequestException(CFMEException):
    """
    Raised if a request was not found or multiple rows matched during _request functions in
    :py:mod:`cfme.services.requests`
    """
    pass


class VmNotFoundViaIP(CFMEException):
    """
    Raised if a specific VM cannot be found.
    """
    pass


class NodeNotFound(CFMEException):
    """Raised if a specific container node cannot be found in the UI"""
    pass


class KeyPairNotFound(CFMEException):
    """
    Raised if a specific cloud key pair cannot be found in the UI
    """
    pass


class OptionNotAvailable(CFMEException):
    """
    Raised if a specified option is not available.
    """
    pass


class UnknownProviderType(CFMEException):
    """
    Raised when the passed provider or provider type is not known or usable in given context
    e.g. when getting a provider from yaml and the provider type doesn't match any of known types
    or when an infra provider is passed to the cloud's instance_factory method
    """
    pass


class CannotScrollException(CFMEException):
    """Raised when even during the heaviest workarounds for scrolling failure comes."""


class CUCommandException(CFMEException):
    """Raised when one of the commands run to set up a CU VM fails """
    pass


class LabelNotFoundException(Exception):
    "Raises when failed to remove label from object via cli"
    pass


class MenuItemNotFound(CFMEException):
    """Raised during navigation of certain menu item was not found."""


class DestinationNotFound(CFMEException):
    """Raised during navigation where the navigator destination is not found"""


class ItemNotFound(CFMEException):
    """Raised when an item is not found in general."""


class ManyEntitiesFound(CFMEException):
    """Raised when one or no items were expected but several/many items were obtained instead."""


class RBACOperationBlocked(CFMEException):
    """
    Raised when a Role Based Access Control operation is blocked from execution due to invalid
    permissions. Also thrown when trying to perform actions CRUD operations on roles/groups/users
    that are CFME defaults
    """


class ChargebackRateNotFound(CFMEException):
    """Raised when a given chargeback (compute or storage) rate is not found during navigation"""


class StatsDoNotMatch(CFMEException):
    """
    Raised if the stats retrieved from CFME do not match those retrieved by wrapanapi
    """
    pass


class CollectionFilteringError(CFMEException):
    """Raised when an action on an un-filtered collection is attempted that requires a filter
    Common example would be navigation to an 'AllForProvider' destination against a collection
    that does not have a provider filter
    """
    def __init__(self, collection, filter_key):
        self.collection = collection
        self.filter_key = filter_key

    def __str__(self):
        return 'Action on Collection ({}) requires a filter: ({})'.format(self.collection,
                                                                          self.filter_key)


class NeedleNotFoundInLog(CFMEException):
    """Raised when log doesnt't contain needle"""


class RestLookupError(CFMEException):
    """raised when lookup of a rest entity fails"""


class SSHExpectTimeoutError(CFMEException):
    """ Raised when SSHExpect Timeouts when waiting for some input. """
    pass


@property
def displayed_not_implemented(cls):
    raise NotImplementedError("This view has no unique markers for is_displayed check")
