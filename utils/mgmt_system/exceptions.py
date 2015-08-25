class ActionNotSupported(Exception):
    """Raised when an action is not supported."""
    pass


class ActionTimedOutError(Exception):
    pass


class ImageNotFoundError(Exception):
    pass


class MultipleImagesError(Exception):
    pass


class NoMoreFloatingIPs(Exception):
    """Raised when provider runs out of FIPs."""


class MultipleInstancesError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RestClientException(Exception):
    pass


class NetworkNameNotFound(Exception):
    pass


class VMInstanceNotCloned(Exception):
    """Raised if a VM or instance is not found."""
    def __init__(self, template):
        self.template = template

    def __str__(self):
        return 'Could not clone %s' % self.template


class VMInstanceNotFound(Exception):
    """Raised if a VM or instance is not found."""
    def __init__(self, vm_name):
        self.vm_name = vm_name

    def __str__(self):
        return 'Could not find a VM/instance named %s.' % self.vm_name


class VMInstanceNotSuspended(Exception):
    """Raised if a VM or instance is not able to be suspended."""
    def __init__(self, vm_name):
        self.vm_name = vm_name

    def __str__(self):
        return 'Could not suspend %s because it\'s not running.' % self.vm_name
