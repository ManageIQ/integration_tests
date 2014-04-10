from contextlib import contextmanager
from copy import deepcopy


def public_fields(o):
    """Returns: a dict of fields whose name don't start with underscore."""

    return dict((key, value) for key, value in o.__dict__.iteritems() if not key.startswith('_'))


def all_public_fields_equal(a, b):
    return public_fields(a) == public_fields(b)


def updates(old, new):
    """Return a dict of fields that are different between old and new."""

    d = {}
    o = public_fields(old)
    for k, v in public_fields(new).items():
        if not v == o[k]:
            d[k] = v
    return d


class Updateable(object):
    """A mixin that helps make an object easily updateable.

    Two Updateables are equal if all their public fields are equal.
    """

    def __eq__(self, other):
        return all_public_fields_equal(self, other)


@contextmanager
def update(obj, *args, **kwargs):
    """Update an object and then sync it with an external application.

    It will deepcopy the object into whatever is named in the 'as'
    clause, run the 'with' code block (which presumably alters the
    object).  Then the update() method on the original object will be
    called with a dict containing only changed fields, and kwargs
    passed to this function.

    If an exception is thrown by update(), the original object will be restored,
    otherwise the updated object will be returned.

    Usage:

        with update(myrecord):
           myrecord.lastname = 'Smith'
           myrecord.address.zipcode = '27707'

    If the object's name is too long, `with` yields the same object so you can use shortcut name
    for it:

        with update(my_fancy_object_with_long_name) as o:
            assert o is my_fancy_object_with_long_name  # :)
            o.name = "Joe"

    """
    if not isinstance(obj, Updateable):
        raise TypeError("update() accepts only objects inherited from Updateable class!")

    original_values = deepcopy(obj)

    yield obj  # Change the original object (`obj`)

    object_updates = updates(original_values, obj)  # Determine changed fields
    if object_updates:
        try:
            obj.update(object_updates, *args, **kwargs)
        except:  # This should not be done but as I just re-raise it after one operation ...
            obj.__dict__ = original_values.__dict__  # Revert
            raise
