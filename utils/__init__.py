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

    @property
    def _lazy(self):
        if not hasattr(self, attr):
            setattr(self, attr, wrapped_method(self))
        return getattr(self, attr)

    @_lazy.setter
    def _lazy(self, value):
        setattr(self, attr, value)

    @_lazy.deleter
    def _lazy(self):
        if hasattr(self, attr):
            delattr(self, attr)

    return _lazy
