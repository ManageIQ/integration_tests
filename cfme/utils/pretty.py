def _name(o):
    cls = o.__class__
    return "{}.{}".format(getattr(cls, '__module__', "module"),
                      getattr(cls, '__name__', "name"))


def attr_repr(o, attr):
    """Return the string repr of the attribute attr on the object o"""
    try:
        return repr(getattr(o, attr, None))
    except BaseException:
        return None


def pretty_repr(attrs, o):
    pairs = zip(attrs, [attr_repr(o, attr) for attr in attrs])
    return "<{} {}>".format(_name(o),
                        ", ".join(["{}={}".format(i[0], i[1]) for i in pairs]))


def pr_obj(attrs):
    def x(o):
        return pretty_repr(attrs, o)
    return x


class Pretty(object):
    """A mixin that prints repr as <MyClass field1=..., field2=...>. The
       fields that will be printed should be stored in the class's
       pretty_attrs attribute (none by default).

    """
    pretty_attrs = []

    def __repr__(self):
        return pretty_repr(self.pretty_attrs, self)
