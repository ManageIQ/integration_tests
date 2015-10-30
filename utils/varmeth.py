# -*- coding: utf-8 -*-
"""Method variant decorator. You specify the desired method variant by a kwarg.

.. code-block:: python

    from utils.varmeth import variable

    class SomeClass(object):
        secret = 42

        @variable
        def mymethod(self):
            print "I am default!"

        @mymethod.variant("foo")
        def i_foo(self):
            print "I foo!"

        @mymethod.variant("bar")
        def in_bar(self):
            print "In bar!"

    s = SomeClass()
    s.mymethod()  # => I am default!
    s.mymethod(method="foo")  # => I foo!
    s.mymethod(method="bar")  # => In bar!
    s.mymethod(method="baz")  # => AttributeError

Original idea:
    Pete Savage

Implementation:
    Milan Falešník
"""


class variable(object):
    """Create a new variable method."""

    def __init__(self, f):
        self._name = f.__name__
        self._mapping = {'default': f}

    def __get__(self, obj, objtype):
        def caller(*args, **kwargs):
            method = kwargs.pop("method", 'default')
            try:
                method = self._mapping[method]
            except KeyError:
                raise AttributeError(
                    "Method {} does not have a variant for {}, valid variants are {}".format(
                        self._name, method, ", ".join(self._mapping.keys())))
            return method(obj, *args, **kwargs)
        return caller

    def variant(self, name):
        """Register a new variant of a method under a name."""
        def g(f):
            self._mapping[name] = f

        return g
