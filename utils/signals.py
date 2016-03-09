""" Simple callback handler routine

Signals are a simple way of notifying the framework that something has happened.
Currently we are using them to notify and take action when we _know_ that certain
caches have become stale and need to be invalidated. The example below shows this.

.. code-block:: python

   import signals
   from fixtures.pytest_store import store

   def invalidate_server_details():
       # TODO: simplify after idempotent cached property is availiable
       # https://github.com/pydanny/cached-property/issues/31
       try:
           del store.current_appliance.configuration_details
       except AttributeError:
           pass
       try:
           del store.current_appliance.zone_description
       except AttributeError:
           pass

   signals.register_callback('server_details_changed', invalidate_server_details)

Or by using a decorator:

.. code-block:: python

   from signals import on_signal
   from fixtures.pytest_store import store

   @on_signal("server_details_changed")
   def invalidate_server_details():
       # TODO: simplify after idempotent cached property is availiable
       # https://github.com/pydanny/cached-property/issues/31
       try:
           del store.current_appliance.configuration_details
       except AttributeError:
           pass
       try:
           del store.current_appliance.zone_description
       except AttributeError:
           pass


Here we create a function to do the work of invalidating the cache and register it
to the signal name 'server_details_changed'. Now whenever something in the framework
changes anything to do with server details it will use the fire function like so.

.. code-block:: python

   import signals

   signals.fire('server_details_changed')

The user who fires off the signal doesn't need to worry about what should happen
when the server details change. They fire the signal and the framework will take the
appropriate action as defined in the callback handler.

Mutliple callbacks can be assigned to the same signal, and can be augmented with args
and kwargs to be able to pass extra information to the callback function.

Current list of signals defined and their usage

====================== ========================================================================
Name                   Usage
====================== ========================================================================
server_details_changed Signal used when the main details of a server has been changed, name etc
server_config_changed  Signal used when the main configuration yaml has been altered
====================== ========================================================================
"""

from collections import defaultdict
from functools import partial
from utils.log import logger


_callback_library = defaultdict(set)


def register_callback(signal, cb_func, *args, **kwargs):
    """ Register a callback function to a signal name

    Args:
        signal: The name of the signal.
        cb_func: The function object to be called.
        args: Any args, passed to the cb_func on calling
        kwargs: Any kwargs, passed to the cb_func on calling
    Returns: A callback object.
    """

    cb_obj = partial(cb_func, *args, **kwargs)
    cb_obj.signal = signal
    _callback_library[signal].add(cb_obj)
    return cb_obj


def on_signal(signal, *args, **kwargs):
    """Decorator for register_callback usage."""
    def g(f):
        return register_callback(signal, f, *args, **kwargs)
    return g


def unregister_callback(cb_obj):
    """ Unregisters a callback object from the library.

    Given a callback object, an attempt will be made to
    remove it from the callback library.

    Args:
        cb_obj: A callback object to be removed.
    """

    try:
        _callback_library[cb_obj.signal].remove(cb_obj)
    except Exception as e:
        logger.exception(e)


def fire(signal):
    """ Fires the signal, invoking all callbacks in the library for the signal.

    Args:
        signal: Name of signal to be invoked.
    """

    logger.info('Invoking callback for signal [{}]'.format(signal))
    for cb_obj in _callback_library.get(signal, set()):
        try:
            cb_obj()
        except Exception as e:
            logger.exception(e)
