# -*- coding: utf-8 -*-
import inspect
import sys
from cached_property import cached_property
from kwargify import kwargify

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
        self.resolve_string_pointers()

    def resolve_string_pointers(self):
        name_mapping = {
            c.__name__: c for c in self.navigation.iterkeys() if not isinstance(c, basestring)}
        updates = {}
        views_to_process = set()
        for cls, transitions in self.navigation.iteritems():
            for transition_name, (targets, args) in transitions.iteritems():
                if any(isinstance(c, basestring) for c in targets):
                    # We have to resolve
                    if cls not in updates:
                        updates[cls] = {}
                    new_targets = []
                    for target in targets:
                        if isinstance(target, basestring):
                            if target not in name_mapping:
                                try:
                                    new_targets.append(self._possible_other_nav_classes[target])
                                except KeyError:
                                    raise NameError('Could not resolve view name {}'.format(target))
                                else:
                                    views_to_process.add(self._possible_other_nav_classes[target])
                            else:
                                new_targets.append(name_mapping[target])
                        else:
                            new_targets.append(target)
                    updates[cls][transition_name] = (tuple(new_targets), args)

        # Updates created, now update the data themselves
        for cls, transitions in updates.iteritems():
            for transition_name, value in transitions.iteritems():
                self.navigation[cls][transition_name] = value

        # Update the views
        if views_to_process:
            for view in views_to_process:
                self.process_view(view)
            # And then resolve the strings again
            self.resolve_string_pointers()

    def process_view(self, view):
        if view in self.navigation:
            return  # Skip because it has already been created
        self.navigation[view] = {}
        for name, targets, args in self.retrieve_transitions_for(view):
            self.navigation[view][name] = (tuple(targets), tuple(args))
            for target in targets:
                if not isinstance(target, basestring):
                    self.process_view(target)
        for subview in view._cls_subviews():
            self.navigation[view].update(self.process_subview_as(subview))

    def process_subview_as(self, view, parent_view_name=None):
        transitions = {}
        if parent_view_name is not None:
            sub_name = '{}.{}'.format(parent_view_name, view.__name__)
        else:
            sub_name = view.__name__
        for name, targets, args in self.retrieve_transitions_for(view):
            transitions['{}.{}'.format(sub_name, name)] = (tuple(targets), tuple(args))
            for target in targets:
                if not isinstance(target, basestring):
                    self.process_view(target)

        for subview in view._cls_subviews():
            transitions.update(
                self.process_subview_as(subview, sub_name))

        return transitions

    def rebuild_navigation(self):
        self.navigation = {}
        self.build_navigation()

    @property
    def _nav_modules(self):
        modules = set()
        for cls in self.navigation.iterkeys():
            modules.add(sys.modules[cls.__module__])
        return modules

    @property
    def _possible_other_nav_classes(self):
        classes = {}
        for module in self._nav_modules:
            for name, cls in inspect.getmembers(module, predicate=inspect.isclass):
                if cls not in self.navigation:
                    classes[name] = cls
        return classes

    def all_paths(self, from_view=None, to_view=None, ignored_views=None):
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
                if len(targets) > 1:
                    # Other possible targets
                    additional_targets = tuple(t for t in targets if t != target)
                else:
                    additional_targets = None
                signature = (name, params, target, additional_targets)
                resulting_paths.append([signature])
                if to_view is not None and target is to_view:
                    continue
                new_ignored_views = {view}
                new_ignored_views.update(ignored_views)
                for path in self.all_paths(
                        from_view=target, to_view=to_view, ignored_views=new_ignored_views):
                    resulting_paths.append([signature] + path)

        if to_view is not None and resulting_paths:
            resulting_paths = filter(lambda path: path[-1][-1] == to_view, resulting_paths)
        return resulting_paths

    def detect_view(self):
        # TODO: Actual detection
        return self.entry_view

    def navigate_to(self, *o, **context):
        if len(o) == 0:
            raise TypeError('You have to pass something')
        if len(o) == 1 and o[0] in self.navigation:
            # A view
            return self.navigate_to_view(self.detect_view(), o[0], context)

    def path_from_to(self, from_view, to_view, given_params):
        paths = []
        for path in self.all_paths(from_view=from_view, to_view=to_view):
            # Disqualify paths based on the variables
            skip = False
            for _, params, _, _ in path:
                for param in params:
                    if param not in given_params:
                        skip = True
            if not skip:
                paths.append(path)

        paths.sort(key=len)
        try:
            path = paths[0]
        except IndexError:
            raise ValueError('Could not find a path!')

        return path

    def instantiate_view(self, view_class, context):
        view = view_class(self, context)
        try:
            view.on_load()
        except AttributeError:
            pass
        return view

    def execute_transition(self, view, name, context):
        levels = name.split('.')
        call = getattr(view, levels.pop(0))
        for level in levels:
            call = getattr(call, level)
        # Call now contains reference to the method
        call = kwargify(call)  # Makes it immune against big dicts and so
        call(**context)

    def navigate_path(self, from_view, final_view, context):
        context = {}
        context.update(self.default_context)
        context.update(context)

        path = self.path_from_to(from_view, final_view, context.keys())
        # Create initial view
        current_view = self.instantiate_view(from_view, context)

        while path:
            transition_name, params, target, additional_targets = path.pop(0)
            self.execute_transition(current_view, transition_name, context)
            if additional_targets:
                view = self.instantiate_view(target, context)
                if view.on_view():
                    # Reinstantiate to execute onload
                    current_view = view
                else:
                    for additional_target in additional_targets:
                        view = self.instantiate_view(additional_target, context)
                        if view.on_view():
                            current_view = view
                            # Reload path from this new place
                            path = self.path_from_to(type(current_view), final_view, context.keys())
                            break
                    else:
                        raise RuntimeError('Landed on an unknown page!')
            else:
                current_view = self.instantiate_view(target, context)

        return current_view
