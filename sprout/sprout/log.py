# -*- coding: utf-8 -*-
from . import sprout_path
import inspect
import sys
from django.db.models import Model
from types import ModuleType
from utils.log import create_logger as _create_logger

log_directory = sprout_path.join("log")


MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_BACKUPS = 10


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

    Args:
        o: Object to create logger for.
        additional_id: If the object does not provide ``pk``, then you can pass this parameter.
    Returns:
        Instance of logger.
    """
    if not log_directory.exists():
        log_directory.mkdir()
    wrap = None
    if isinstance(o, basestring):
        if o in sys.modules:
            # str -> module
            return create_logger(sys.modules[o], additional_id)
        logger_name = o
        file_name = log_directory.join(logger_name + ".log").strpath
    elif isinstance(o, ModuleType):
        module_name = o.__name__.replace(".", "_")
        logger_name = module_name
        file_name = log_directory.join(module_name + ".log").strpath
        if additional_id is not None:
            wrap = LogWrapperForObject
    else:
        module_name = o.__module__.replace(".", "_")
        try:
            o_name = o.__name__
        except AttributeError:
            o_name = type(o).__name__
        logger_name = "{}.{}".format(module_name, o_name)
        module_folder = log_directory.join(module_name)
        if not module_folder.exists():
            module_folder.mkdir()
        file_name = module_folder.join("{}.log".format(o_name)).strpath
        if isinstance(o, Model) or (inspect.isclass(o) and issubclass(o, Model)):
            wrap = LogWrapperForObject
    result = _create_logger(
        logger_name, filename=file_name, max_file_size=MAX_FILE_SIZE, max_backups=MAX_BACKUPS)
    if wrap:
        return wrap(result, o, additional_id)
    else:
        return result
