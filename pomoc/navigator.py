# -*- coding: utf-8 -*-
from .browser import Browser


class NavigatorState(dict):
    def __setattr__(self, attr, value):
        self[attr] = value

    def __getattr__(self, attr):
        return None


class Navigator(object):
    @classmethod
    def register_view(cls, view):
        try:
            cls.view_classes
        except AttributeError:
            cls.view_classes = {}

        try:
            cls.view_classes_changes
        except AttributeError:
            cls.view_classes_changes = 0

        if view.__name__ in cls.view_classes:
            raise NameError('{} is already registered View name'.format(view.__name__))
        cls.view_classes[view.__name__] = view
        cls.view_classes_changes += 1
        return view

    @staticmethod
    def transition_to(o):
        def g(f):
            if not hasattr(f, '_navigator'):
                f._navigator = {}
            f._navigator['transition_to'] = o
            return f
        return g

    def __init__(self, root_object, entry_view):
        self.root_object = root_object
        self.entry_view = entry_view
        self.state = NavigatorState()
        self.browser = Browser(self.root_object.selenium)
        self._navigation = None
        self._navigation_change_id = None

    @property
    def navigation(self):
        if (
                self._navigation is None or
                self._navigation_change_id is None or
                self._navigation_change_id < self.view_classes_changes):
            self._rebuild_navigation()
        return self._navigation

    @navigation.deleter
    def navigation(self):
        self._navigation = None

    def _rebuild_navigation(self):
        pass

    def navigate_to(self, *o, **additional_context):
        pass
