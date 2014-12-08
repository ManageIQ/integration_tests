""" Simple callback handler routine """

from collections import defaultdict
from functools import partial
from utils.log import logger


_callback_library = defaultdict(set)


def register_callback(signal, cb_func, *args, **kwargs):
    cb_obj = partial(cb_func, *args, **kwargs)
    cb_obj.signal = signal
    _callback_library[signal].add(cb_obj)
    return cb_obj


def unregister_callback(cb_obj):
    try:
        _callback_library[cb_obj.signal].remove(cb_obj)
    except Exception as e:
        print e


def fire(signal):
    for cb_obj in _callback_library[signal]:
        try:
            cb_obj()
        except Exception as e:
            logger.exception(e)
