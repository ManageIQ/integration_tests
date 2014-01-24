"""
utils.log
---------

This module creates the cfme logger, for use throughout the project. This logger only captures log
messages explicitly sent to it, not logs emitted by other components (such as selenium). To capture
those, consider using the pytest-capturelog plugin.

Usage:

    from utils.log import logger

    logger.debug('debug log message')
    logger.info('info log message')
    logger.warning('warning log message')
    logger.error('error log message')
    logger.critical('critical log message')

The above will result in the following output in ``cfme_tests/logs/cfme.log``:

    1970-01-01 00:00:00,000 [D] debug log message (filename.py:3)
    1970-01-01 00:00:00,000 [I] info log message (filename.py:4)
    1970-01-01 00:00:00,000 [W] warning log message (filename.py:5)
    1970-01-01 00:00:00,000 [E] error log message (filename.py:6)
    1970-01-01 00:00:00,000 [C] fatal log message (filename.py:7)

Additionally, if ``log_error_to_console`` is True (see below), the following will be
written to stderr:

    [E] error (filename.py:6)
    [C] fatal (filename.py:7)


Configuration
^^^^^^^^^^^^^

.. code-block:: yaml

    # in env.yaml
    logging:
        # Can be one of DEBUG, INFO, WARNING, ERROR, CRITICAL
        level: INFO
        # Maximum logfile size, in bytes, before starting a new logfile
        # Set to 0 to disable log rotation
        max_logfile_size: 0
        # Maximimum backup copies to make of rotated log files (e.g. cfme.log.1, cfme.log.2, ...)
        # Set to 0 to keep no backups
        max_logfile_backups: 0
        # If True, messages of level ERROR and CRITICAL are also written to stderr
        log_errors_to_console: False

Message Format
^^^^^^^^^^^^^^

    ``year-month-day hour:minute:second,millisecond [Level] message text (file:linenumber)``

``[Level]``:

    One letter in square brackets, where ``[I]`` corresponds to INFO, ``[D]`` corresponds to
    DEBUG, and so on.

``(file:linenumber)``:

    The relative location from which this log message was emitted. Paths outside

Members
^^^^^^^

"""
import logging
from logging.handlers import RotatingFileHandler


from utils.conf import env
from utils.path import get_rel_path, log_path


# Pull in config values/set defaults
logging_conf = env.get('logging', {})
log_level = logging_conf.get('level', 'INFO')
max_logfile_size = logging_conf.get('max_file_size', 0)
max_logfile_backups = logging_conf.get('max_file_backups', 0)
log_errors_to_console = logging_conf.get('errors_to_console', False)


class RelpathFilter(logging.Filter):
    """Adds the relpath attr to records

    Not actually a filter, this was the least ridiculous way to add custom dynamic
    record attributes.

    """
    def filter(self, record):
        record.relpath = get_rel_path(record.pathname)
        return True


def create_logger(logger_name):
    """Creates and returns the named logger

    Used to create the cfme logger, this can be used to create other loggers, if desired.

    """
    log_path.ensure(dir=True)
    log_file = str(log_path.join('%s.log' % logger_name))

    relpath_filter = RelpathFilter()

    # log_file is dynamic, so we can't used logging.config.dictConfig here without creating
    # a custom RotatingFileHandler class. At some point, we should do that, and move the
    # entire logging config into env.yaml
    file_format = '%(asctime)-15s [%(levelname).1s] %(message)s (%(relpath)s:%(lineno)d)'
    file_formatter = logging.Formatter(file_format)
    file_handler = RotatingFileHandler(log_file, maxBytes=max_logfile_size, encoding='utf8')
    file_handler.setFormatter(file_formatter)

    stream_format = '[%(levelname)s] %(message)s (%(relpath)s:%(lineno)d)'
    stream_formatter = logging.Formatter(stream_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.ERROR)
    stream_handler.setFormatter(stream_formatter)

    logger = logging.getLogger(logger_name)
    logger.addHandler(file_handler)
    logger.setLevel(log_level)
    if log_errors_to_console:
        logger.addHandler(stream_handler)
    logger.addFilter(relpath_filter)
    return logger

logger = create_logger('cfme')
