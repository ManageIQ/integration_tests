from contextlib import contextmanager
from copy import deepcopy


def public_fields(o):
    """
    Returns: a dict of fields whose name don't start with underscore.
    """

    return dict((key, value) for key, value in o.__dict__.iteritems() if not key.startswith('_'))


def all_public_fields_equal(a, b):
    return public_fields(a) == public_fields(b)


def updates(old, new):
    """
    Return a dict of fields that are different between old and new.
    """

    d = {}
    o = public_fields(old)
    for k, v in public_fields(new).items():
        if not v == o[k]:
            d[k] = v
    return d


class Updateable(object):
    """
    A mixin that helps make an object easily updateable. Two Updateables
    are equal if all their public fields are equal.
    """

    def __eq__(self, other):
        return all_public_fields_equal(self, other)


@contextmanager
def update(o, **kwargs):
    """
    Update an object and then sync it with an external application.

    It will deepcopy the object into whatever is named in the 'as'
    clause, run the 'with' code block (which presumably alters the
    object).  Then the update() method on the original object will be
    called with a dict containing only changed fields, and kwargs
    passed to this function.

    If an exception is thrown by update(), the original object will be restored,
    otherwise the updated object will be returned.

    Usage:
    with update(myrecord) as myrecord:
       myrecord.lastname = 'Smith'
       myrecord.address.zipcode = '27707'

    """
    cp = deepcopy(o)
    yield cp
    o_updates = updates(o, cp)
    if o_updates:
        o.update(o_updates, **kwargs)
        o.__dict__ = cp.__dict__
