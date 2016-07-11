# -*- coding: utf-8 -*-
import inspect
from cached_property import cached_property

from .browser import Browser


class NavigatorState(dict):
    def __setattr__(self, attr, value):
        self[attr] = value

    def __getattr__(self, attr):
        return None


class Navigator(object):
    @staticmethod
    def transition_to(*view_classes):
        def g(f):
            if not hasattr(f, '_navigator'):
                f._navigator = {}
            f._navigator['transition_to'] = list(view_classes)
            return f
        return g

    @staticmethod
    def retrieve_transitions_for(view_class):
        for name, method in inspect.getmembers(view_class, predicate=inspect.ismethod):
            if not hasattr(method, '_navigator'):
                continue
            argnames = inspect.getargspec(method).args[1:]
            if 'transition_to' in method._navigator:
                if len(method._navigator['transition_to']) > 1:
                    bad_views = []
                    for view in method._navigator['transition_to']:
                        if isinstance(view, basestring):
                            raise ValueError('Circular resolution using strings not supported yet.')
                        if not hasattr(view, 'on_view') or not inspect.ismethod(view.on_view):
                            bad_views.append(view.__name__)
                    if bad_views:
                        raise TypeError(
                            ('Since {}.{} defines multiple transitions, classes {} must define a '
                            'on_view method').format(
                                view_class.__name__, name, ', '.join(bad_views)))
                yield name, method._navigator['transition_to'], argnames

    def __init__(self, root_object, entry_view):
        self.root_object = root_object
        if not hasattr(entry_view, 'on_load'):
            raise ValueError('The entry view does not have on_load method.')
        self.entry_view = entry_view
        self.state = NavigatorState()
        self.navigation = {}
        self.build_navigation()

    @cached_property
    def browser(self):
        return Browser(self.root_object.selenium)

    def build_navigation(self):
        if self.navigation:
            raise ValueError(
                'Navigation is already built. You probably wanted to use clear_navigation?')
        self.process_view(self.entry_view)

    def process_view(self, view):
        if view in self.navigation:
            return  # Skip because it has already been created
        self.navigation[view] = {}
        for name, targets, args in self.retrieve_transitions_for(view):
            self.navigation[view][name] = (tuple(targets), tuple(args))
            for target in targets:
                self.process_view(target)

    def clear_navigation(self):
        self.navigation = {}
        self.build_navigation()

    def navigate_to(self, *o, **additional_context):
        pass
