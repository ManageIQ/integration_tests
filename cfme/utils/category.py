# -*- coding: utf-8 -*-
"""Module used for handling categories of let's say form values and for categorizing them."""


class CategoryBase(object):
    """Base class for categories

    Args:
        value: Value to be categorized.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(repr(self.value)))


def categorize(iterable, cat):
    """Function taking iterable of values and a dictionary of rules to categorize the values.

    Keys of the dictionary are callables, taking one parameter - the current iterable item. If the
    call on it returns positive, then the value part of dictionary is taken (assumed callable)
    and it is called with the current item.

    Args:
        iterable: Iterable to categorize.
        cat: Category specification dictionary
    """
    for item in iterable:
        for cond, func in cat.iteritems():
            if callable(cond) and cond(item):
                func(item)
                break
        else:
            cat.get("default", lambda item: None)(item)
