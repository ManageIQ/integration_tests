# -*- coding: utf-8 -*-
import inspect
from smartloc import Locator
from threading import Lock
from wait_for import wait_for

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
            return self

        # Cache on LocatorDescriptor
        if self not in obj._widget_cache:
            obj._widget_cache[self] = self.klass(obj, *self.args, **self.kwargs)
        return obj._widget_cache[self]

    def __repr__(self):
        if self.args:
            args = ', ' + ', '.join(repr(arg) for arg in self.args)
        else:
            args = ''
        if self.kwargs:
            kwargs = ', ' + ', '.join(
                '{}={}'.format(k, repr(v)) for k, v in self.kwargs.iteritems())
        else:
            kwargs = ''
        return '{}({}{}{})'.format(type(self).__name__, self.klass.__name__, args, kwargs)


class Widget(object):
    def __new__(cls, *args, **kwargs):
        """Implement some typing saving magic.

        Unless you are passing a View or Navigator as a first argument which implies the
        instantiation of an actual widget, it will return LocatorDescriptor instead which will
        resolve automatically inside of View instance.
        """
        if args and isinstance(args[0], (View, Navigator)):
            return super(Widget, cls).__new__(cls, *args, **kwargs)
        else:
            return LocatorDescriptor(cls, *args, **kwargs)

    def __init__(self, parent):
        self.parent = parent

    @property
    def browser(self):
        try:
            return self.parent.browser
        except AttributeError:
            raise ValueError('Unknown value {} specified as parent.'.format(repr(self.parent)))

    @property
    def parent_view(self):
        if isinstance(self.parent, View):
            return self.parent
        else:
            return None

    @property
    def is_displayed(self):
        return self.browser.is_displayed(self)

    def wait_displayed(self):
        wait_for(lambda: self.is_displayed, timeout='15s', delay=0.2)

    def move_to_element(self):
        return self.browser.move_to_element(self)

    def __locator__(self):
        raise NotImplementedError('You have to implement __locator__ or __element__')

    def __element__(self):
        """Default functionality, resolves :py:meth:`__locator__`."""
        return self.browser.element(self)


def _gen_locator_meth(loc):
    def __locator__(self):
        return loc
    return __locator__


class ViewMetaclass(type):
    def __new__(cls, name, bases, attrs):
        new_attrs = {}
        for key, value in attrs.iteritems():
            if inspect.isclass(value) and getattr(value, '__metaclass__', None) is cls:
                new_attrs[key] = LocatorDescriptor(value)
            else:
                new_attrs[key] = value
        if 'ROOT' in new_attrs:
            # For handling the root locator of the View
            rl = Locator(new_attrs['ROOT'])
            new_attrs['__locator__'] = _gen_locator_meth(rl)
        return super(ViewMetaclass, cls).__new__(cls, name, bases, new_attrs)


class View(object):
    __metaclass__ = ViewMetaclass

    def __init__(self, parent, additional_context=None):
        self.parent = parent
        self.context = additional_context or {}
        self._widget_cache = {}

    def flush_widget_cache(self):
        # Recursively ...
        for view in self._views:
            view._widget_cache.clear()
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
    def _views(self):
        return [view for view in self if isinstance(view, View)]

    @classmethod
    def _cls_subviews(cls):
        for widget_attr in cls.widget_names():
            c = getattr(cls, widget_attr)
            if isinstance(c, LocatorDescriptor) and issubclass(c.klass, View):
                yield c.klass

    @property
    def navigator(self):
        if isinstance(self.parent, View):
            return self.parent.navigator
        else:
            return self.parent

    @property
    def browser(self):
        return self.navigator.browser.in_parent_context(self.element_parents)

    @property
    def resolvable(self):
        return hasattr(self, '__locator__') or hasattr(self, '__element__')

    @property
    def element_parents(self):
        """Returns a chain of resolvable views used to query elements."""
        this = [self] if self.resolvable else []
        if isinstance(self.parent, View):
            return self.parent.element_parents + this
        else:
            return this

    def __iter__(self):
        for widget_attr in self.widget_names():
            yield getattr(self, widget_attr)
