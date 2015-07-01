# -*- coding: utf-8 -*-
import atexit
import logging
import logging.handlers
from threading import Lock

import inspect
import sys
from django.db.models import Model
from types import ModuleType

logger_cache = {}
logger_cache_lock = Lock()


class LogWrapperForObject(object):
    """This class masks the logger in order to print out the id of the object to identify it.

    Args:
        logger: The logger to mask
        o: The object that the logger was made for
        id: If the object is not likely to provide ``pk`` on its own, then pass something here
    """
    WRAPPED_FIELDS = ["trace", "debug", "info", "warning", "error", "exception"]

    def __init__(self, logger, o, id=None):
        self._logger = logger
        self._o = o
        self._id = id

    def __getattr__(self, attr):
        if attr not in self.WRAPPED_FIELDS:
            raise AttributeError("Could not find {}".format(attr))
        result = getattr(self._logger, attr)

        def _log(s, *args, **kwargs):
            if self._id is not None:
                s = "[{}] {}".format(self._id, s)
            elif hasattr(self._o, "pk"):
                s = "[{}] {}".format(self._o.pk, s)
            else:
                s = "[{}] {}".format(str(self._o), s)
            return result(s, *args, **kwargs)
        return _log


def create_logger(o, additional_id=None):
    """Creates a logger that has its filename derived from the passed object's properties.

    The logger is targeted at the logserver.

    Args:
        o: Object to create logger for.
        additional_id: If the object does not provide ``pk``, then you can pass this parameter.
    Returns:
        Instance of logger.
    """
    wrap = None
    if isinstance(o, basestring):
        if o in sys.modules:
            # str -> module
            return create_logger(sys.modules[o], additional_id)
        logger_name = o
    elif isinstance(o, ModuleType):
        module_name = o.__name__
        logger_name = module_name
        if additional_id is not None:
            wrap = LogWrapperForObject
    else:
        module_name = o.__module__
        try:
            o_name = o.__name__
        except AttributeError:
            o_name = type(o).__name__
        logger_name = "{}.{}".format(module_name, o_name)
        if isinstance(o, Model) or (inspect.isclass(o) and issubclass(o, Model)):
            wrap = LogWrapperForObject
    with logger_cache_lock:
        if None not in logger_cache:
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
            socket_handler = logging.handlers.SocketHandler(
                "localhost", logging.handlers.DEFAULT_TCP_LOGGING_PORT)
            atexit.register(socket_handler.close)
            logger.addHandler(socket_handler)
            logger_cache[None] = logger
        if logger_name not in logger_cache:
            logger_cache[logger_name] = logging.getLogger(logger_name)
        result = logger_cache[logger_name]
    if wrap:
        return wrap(result, o, additional_id)
    else:
        return result
