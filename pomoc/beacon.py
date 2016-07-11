# -*- coding: utf-8 -*-
import logging
from kwargify import kwargify


def funcname(f):
    try:
        return f.func_name
    except AttributeError:
        try:
            return f.__name__
        except AttributeError:
            return '(unknown)'


class Signal(object):
    def __init__(self, name, required_variables=(), suppressed_exceptions=(), logger=None):
        self.name = name
        self.required_variables = required_variables
        self.callbacks = []
        self.suppressed_exceptions = tuple(suppressed_exceptions)
        self.logger = logger or logging.getLogger('beacon')

    def register(self, callback):
        if callback in self.callbacks:
            raise ValueError('Callback {} is already registered!'.format(repr(callback)))
        self.callbacks.append(kwargify(callback))

    def trigger(self, **arguments):
        for required_variable in self.required_variables:
            if required_variable not in arguments:
                raise TypeError(
                    'Signal {} needs an argument {}'.format(self.name, required_variable))
        kwargs = {'state': {
            'total_callbacks': len(self.callbacks),
            'suppress_exception': False,
            'callbacks_run': 0,
            'callbacks_errors_suppressed': 0}}
        kwargs.update(arguments)
        for cb in self.callbacks:
            try:
                cb(**kwargs)
            except self.suppressed_exceptions as e:
                self.logger.warning('Known exception suppressed: %s: %s', type(e).__name__, str(e))
                kwargs['state']['callbacks_errors_suppressed'] += 1
            except Exception as e:
                self.logger.error(
                    'Callback %s for signal %s failed with an exception', funcname(cb), self.name)
                self.logger.exception(e)
                raise
            else:
                kwargs['state']['callbacks_run'] += 1
        return kwargs['state']


navigation_started = Signal('navigation_started')
before_element_query = Signal('before_element_query')
element_found = Signal('element_found')
element_not_found = Signal('element_not_found')
