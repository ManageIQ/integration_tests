# -*- coding: utf-8 -*-
import inspect
from smartloc import Locator
from threading import Lock

from .navigator import Navigator


class LocatorDescriptor(object):
    _seq_cnt = 0
    _seq_cnt_lock = Lock()

    def __new__(cls, *args, **kwargs):
        o = super(LocatorDescriptor, cls).__new__(cls)
        with LocatorDescriptor._seq_cnt_lock:
            o._seq_id = LocatorDescriptor._seq_cnt
            LocatorDescriptor._seq_cnt += 1
        return o

    def __init__(self, klass, *args, **kwargs):
        self.klass = klass
        self.args = args
        self.kwargs = kwargs

    def __get__(self, obj, type=None):
        if obj is None:  # class access
            return self.klass

        # Cache on LocatorDescriptor
        if self not in obj._widget_cache:
            obj._widget_cache[self] = self.klass(obj, *self.args, **self.kwargs)
        return obj._widget_cache[self]


class Widget(object):
    def __new__(cls, *args, **kwargs):
        """Implement some typing saving magic.

        Unless you are passing a View as a first argument which implies the instantiation of an
        actual widget, it will return LocatorDescriptor instead which will resolve automatically
        inside of View instance.
        """
        if args and isinstance(args[0], View):
            return super(Widget, cls).__new__(cls, *args, **kwargs)
        else:
            return LocatorDescriptor(cls, *args, **kwargs)

    def __init__(self, parent):
        self.parent = parent

    def __locator__(self):
        raise NotImplementedError('You have to implement __locator__ or __element__')

    def __element__(self):
        return Locator(self).find_element(self.parent.browser)


class ViewMetaclass(type):
    def __new__(cls, name, bases, attrs):
        new_attrs = {}
        for key, value in attrs.iteritems():
            if inspect.isclass(value) and getattr(value, '__metaclass__', None) == cls:
                new_attrs[key] = LocatorDescriptor(value)
            else:
                new_attrs[key] = value
        return super(ViewMetaclass, cls).__new__(cls, name, bases, new_attrs)


class View(object):
    __metaclass__ = ViewMetaclass

    def __init__(self, parent):
        self.parent = parent
        self._widget_cache = {}

    def flush_widget_cache(self):
        self._widget_cache.clear()

    @classmethod
    def widget_names(cls):
        result = []
        for key in dir(cls):
            value = getattr(cls, key)
            if isinstance(value, LocatorDescriptor):
                result.append((key, value))
        return [name for name, _ in sorted(result, key=lambda pair: pair[1]._seq_id)]

    @property
    def navigator(self):
        if isinstance(self.parent, Navigator):
            return self.parent
        else:
            return self.parent.navigator

    @property
    def browser(self):
        return self.navigator.browser

    def __iter__(self):
        for widget_attr in self.widget_names:
            yield getattr(self, widget_attr)
