# -*- coding: utf-8 -*-
"""Method variant decorator. You specify the desired method variant by a kwarg.

.. code-block:: python

    from utils.varmeth import variable

    class SomeClass(object):
        secret = 42

        @variable
        def mymethod(self):
            print("I am default!")

        @mymethod.variant("foo", "foo_too")
        def i_foo(self):
            print("I foo!")

        @mymethod.variant("bar")
        def in_bar(self):
            print("In bar!")

        @variable(alias="foo")
        def myfoo(self):
            print("foo!")

    s = SomeClass()
    s.mymethod()  # => I am default!
    s.mymethod(method="moo")  # => I am default!
    s.mymethod(method="foo")  # => I foo!
    s.mymethod(method="foo_too")  # => I foo!
    s.mymethod(method="bar")  # => In bar!
    s.mymethod(method="baz")  # => AttributeError
    s.myfoo()  # => foo!
    s.myfoo(method="foo")  # => foo!

Original idea:
    Pete Savage

Implementation:
    Milan Falešník
"""


class _default(object):
    """Whoever touches this outside of this module, his/her hands will fall off."""


class variable(object):
    """Create a new variable method."""

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            # Decorator without parameters
            f = args[0]
            self._name = f.__name__
            self._mapping = {_default: f}
            self._alias = None
        else:
            # Decorator with parameters, the default function comes later in __call__
            self._name = None
            self._mapping = {}
            self._alias = kwargs.get("alias", None)

    def __call__(self, f):
        if _default in self._mapping:
            raise ValueError("You cannot set the default twice!")
        self._mapping[_default] = f
        if self._alias is not None:
            self._mapping[self._alias] = f
        return self

    def __get__(self, obj, objtype):
        def caller(*args, **kwargs):
            method = kwargs.pop("method", _default)
            if not method:
                method = _default
            try:
                method = self._mapping[method]
            except KeyError:
                raise AttributeError(
                    "Method {} does not have a variant for {}, valid variants are {}".format(
                        self._name, method, ", ".join(map(str, self._mapping.keys()))))
            return method(obj, *args, **kwargs)
        return caller

    def variant(self, *names):
        """Register a new variant of a method under a name."""
        def g(f):
            for name in names:
                self._mapping[name] = f

        return g
