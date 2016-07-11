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
        self.default_context = {}
        self.navigation = {}
        self.build_navigation()

    @cached_property
    def browser(self):
        return Browser(self.root_object.selenium)

    def build_navigation(self):
        if self.navigation:
            raise ValueError(
                'Navigation is already built. You probably wanted to use rebuild_navigation?')
        self.process_view(self.entry_view)

    def process_view(self, view):
        if view in self.navigation:
            return  # Skip because it has already been created
        self.navigation[view] = {}
        for name, targets, args in self.retrieve_transitions_for(view):
            self.navigation[view][name] = (tuple(targets), tuple(args))
            for target in targets:
                self.process_view(target)

    def rebuild_navigation(self):
        self.navigation = {}
        self.build_navigation()

    def all_paths(self, from_view=None, ignored_views=None):
        view = from_view or self.entry_view
        ignored_views = ignored_views or set()

        try:
            transitions = self.navigation[view]
        except KeyError:
            raise NameError('No such view {} in the navigator'.format(repr(view)))

        resulting_paths = []
        for name, (targets, params) in transitions.iteritems():
            for target in targets:
                if target in ignored_views:
                    continue
                signature = (name, params, target)
                resulting_paths.append([signature])
                new_ignored_views = {view}
                new_ignored_views.update(ignored_views)
                for path in self.all_paths(target, new_ignored_views):
                    resulting_paths.append([signature] + path)

        return resulting_paths

    def navigate_to(self, *o, **additional_context):
        if len(o) == 0:
            raise TypeError('You have to pass something')
        if len(o) == 1 and o[0] in self.navigation:
            # A view
            return self.navigate_to_view(o[0], **additional_context)

    def navigate_to_view(self, view, **additional_context):
        context = {}
        context.update(self.default_context)
        context.update(additional_context)

        paths = []
        for path in self.all_paths(from_view=view):
            # Disqualify paths based on the variables
            skip = False
            for _, params, _ in path:
                for param in params:
                    if param not in context:
                        skip = True
            if not skip:
                paths.append(path)

        paths.sort(key=len)
        try:
            path = paths[0]
        except IndexError:
            raise ValueError('Could not find a path!')

        self.navigate_path(view, path, **context)

    def navigate_path(self, from_view, path, context):
        pass
