"""Class to parametrize and dereference strings for CFME UI messages"""
import six


class ParametrizedString():
    """Class for a string with formatters that will be dereferenced to the parent object on
    access"""

    def __init__(self, string, obj):
        if not isinstance(string, six.string_types):
            raise ValueError('Must pass string')

        self.string = string
        self.context = obj

    def __get__(self):
        pass
