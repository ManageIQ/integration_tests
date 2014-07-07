from functools import partial


def _name(o):
    cls = o.__class__
    return "%s.%s" % (getattr(cls, '__module__', "module"),
                      getattr(cls, '__name__', "name"))


def attr_repr(o, attr):
    '''Return the string repr of the attribute attr on the object o'''
    return repr(getattr(o, attr, None))


def pretty_repr(attrs, o):
    attr_repr_o = partial(attr_repr, o)
    pairs = zip(attrs, map(attr_repr_o, attrs))
    return "<%s %s>" % (_name(o),
                        ", ".join(map(lambda i: "%s=%s" % (i[0], i[1]), pairs)))


def pr_obj(attrs):
    def x(o):
        return pretty_repr(attrs, o)
    return x


class Pretty(object):
    '''A mixin that prints repr as <MyClass field1=..., field2=...>. The
       fields that will be printed should be stored in the class's
       pretty_attrs attribute (none by default).

    '''
    pretty_attrs = []

    def __repr__(self):
        return pretty_repr(self.pretty_attrs, self)
