def lazycache(wrapped_method):
    """method decorator to create a lazily-evaluated and cached property

    ``lazycache``'d properties are complete object descriptors, supporting
    ``get``, ``set``, and ``del``, though ``del`` will clear a property's cache rather
    than destroy the property entirely

    Usage:

        >>> from utils import lazycache
        >>> class Example(object):
        ...     @lazycache
        ...     def lazyprop(self):
        ...             return '42'
        ...
        >>> ex = Example()
        >>> value = ex.lazyprop
        >>> print value
        42
        >>> print value is ex.lazyprop
        # lazyprop guarantees this to be True, normal properties do not.
        True
        >>> ex.lazyprop = '99'
        >>> print ex.lazyprop
        # setting works!
        99
        >>> del(ex.lazyprop)
        >>> print ex.lazyprop
        # deleting clears the cache, so the value is recomputed on the next call
        42

    Values are stored in a private attribute of the same name as the method being decorated,
    e.g. a decorated method named ``lazyprop`` will store its cached value in an attr
    called ``_lazyprop``
    """
    attr = '_' + wrapped_method.__name__

    if wrapped_method.__doc__:
        doc = wrapped_method.__doc__ + '\n\nThis attribute is lazily evaluated and cached.'
    else:
        doc = None

    def get_lazy(self):
        if not hasattr(self, attr):
            setattr(self, attr, wrapped_method(self))
        return getattr(self, attr)

    def set_lazy(self, value):
        setattr(self, attr, value)

    def del_lazy(self):
        if hasattr(self, attr):
            delattr(self, attr)

    lazy = property(get_lazy, set_lazy, del_lazy, doc)
    return lazy
