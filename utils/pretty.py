# -*- coding: utf-8 -*-
import collections


def _name(o):
    cls = o.__class__
    return "%s.%s" % (getattr(cls, '__module__', "module"),
                      getattr(cls, '__name__', "name"))


def attr_repr(o, attr):
    """Return the string repr of the attribute attr on the object o"""
    try:
        return repr(getattr(o, attr, None))
    except BaseException:
        return None


def pretty_repr(attrs, o):
    pairs = zip(attrs, [attr_repr(o, attr) for attr in attrs])
    return "<%s %s>" % (_name(o),
                        ", ".join(["%s=%s" % (i[0], i[1]) for i in pairs]))


def pr_obj(attrs):
    def x(o):
        return pretty_repr(attrs, o)
    return x


def process_attrs(attrs):
    """Enables us for more freedom in attribute specification"""
    if attrs is None:
        return []
    elif isinstance(attrs, collections.Sequence):
        return list(attrs)
    else:
        raise TypeError(
            "pretty_attrs should be tuple, list or None, not {}".format(type(attrs).__name__))


class Pretty(object):
    """A mixin that prints repr as <MyClass field1=..., field2=...>. Provides default constructor

    The fields that will be printed should be stored in the class's pretty_attrs attribute
    (none by default). It also provides a default constructor for the values specified.

    the ``pretty_attrs`` can be list, tuple or None. The ``required_attrs`` is a list of
    attributes that are required for a successful construction of the object, same structure as
    pretty_attrs. ``default_attrs`` is a dictionary of default values. Keys must exist in
    ``pretty_attrs`` for it to work.
    """
    pretty_attrs = None
    required_attrs = None
    default_attrs = {}

    def __init__(self, *args, **kwargs):
        """Default constructor providing data copying from arguments to the instance.

        Can process both positional arguments, as ordered in ``pretty_attrs``, and keyword arguments
        that will eventually overwrite the attributes set with the positional one.
        """
        pretty_attrs = process_attrs(type(self).pretty_attrs)
        # Load defaults
        for attr, value in type(self).default_attrs.iteritems():
            if attr not in pretty_attrs:
                raise NameError("No such attribute {}!".format(attr))
            setattr(self, attr, value)
        if len(args) > len(pretty_attrs):
            raise ValueError("More attributes provided than it is possible to process!")
        # Load the positional args
        for attr, value in zip(pretty_attrs, args):
            setattr(self, attr, value)
        # Load the dictionary args
        for attr, value in kwargs.iteritems():
            # Chack against unwanted data
            if attr not in pretty_attrs:
                raise NameError("No such field {}".format(attr))
            setattr(self, attr, value)
        # Check required attributes are present
        required_attrs = process_attrs(type(self).required_attrs)
        for attr in required_attrs:
            if not hasattr(self, attr):
                raise NameError("Required attribute {} not specified!".format(attr))

    def __repr__(self):
        return pretty_repr(process_attrs(self.pretty_attrs), self)
