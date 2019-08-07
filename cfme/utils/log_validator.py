import re
from contextlib import contextmanager

from cfme.utils.log import logger
from cfme.utils.ssh import SSHTail
from cfme.utils.wait import wait_for


class FailPatternMatchError(Exception):
    """Custom exception for LogValidator"""

    def __init__(self, pattern, message, line):
        self.pattern = pattern
        self.message = message
        self.line = line

    def __str__(self):
        return repr("Pattern '{p}': {m}".format(p=self.pattern, m=self.message))


class LogValidator(object):
    """
    Log content validator class provides methods
    to monitor the log content before test is started,
    and validate the content of log during test execution,
    according to predefined patterns.
    Predefined patterns are:

    * Logs which should be skipped. Skip further checks on particular line if matched
    * Logs which should cause failure of test.
    * Logs which are expected to be matched, otherwise fail.

    The priority of patterns to be checked are defined in above order.
    Skipping patterns have priority over other ones,
    to be possible to skip particular ERROR log,
    but fail for wider range of other ERRORs.

    Note: If failures pattern matched in log; It will raise `FailPatternMatchError`

    Args:
        remote_filename: path to the remote log file
        skip_patterns: array of skip regex patterns
        failure_patterns: array of failure regex patterns
        matched_patterns: array of expected regex patterns to be matched

    Usage:
        .. code-block:: python
          evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                                  skip_patterns=['PARTICULAR_ERROR'],
                                  failure_patterns=['.*ERROR.*'],
                                  matched_patterns=['PARTICULAR_INFO'])
          evm_tail.start_monitoring()
          evm_tail.validate()       # evm_tail.validate(wait="30s")
    """

    def __init__(self, remote_filename, **kwargs):
        self.skip_patterns = kwargs.pop('skip_patterns', [])
        self.failure_patterns = kwargs.pop('failure_patterns', [])
        self.matched_patterns = kwargs.pop('matched_patterns', [])

        self._remote_file_tail = SSHTail(remote_filename, **kwargs)
        self._matches = {key: 0 for key in self.matched_patterns}

    def start_monitoring(self):
        """Start monitoring log before action"""
        self._remote_file_tail.set_initial_file_end()
        logger.info("Log monitoring has been started on remote file")

    def _check_skip_logs(self, line):
        for pattern in self.skip_patterns:
            if re.search(pattern, line):
                logger.info(
                    "Skip pattern %s was matched on line %s so skipping this line", pattern, line
                )
                return True
        return False

    def _check_fail_logs(self, line):
        for pattern in self.failure_patterns:
            if re.search(pattern, line):
                logger.error("Failure pattern %s was matched on line %s", pattern, line)
                raise FailPatternMatchError(pattern, "Expected failure pattern found in log.", line)

    def _check_match_logs(self, line):
        for pattern in self.matched_patterns:
            if re.search(pattern, line):
                logger.info("Expected pattern %s was matched on line %s", pattern, line)
                self._matches[pattern] = self._matches[pattern] + 1

    @property
    def _is_valid(self):
        for pattern, count in self.matches.items():
            if count == 0:
                logger.info("Expected '%s' pattern not found", pattern)
                return False
        return True

    @property
    def matches(self):
        """Collect match count in log

        Returns (dict): Pattern match count dictionary
        """

        for line in self._remote_file_tail:
            if self._check_skip_logs(line):
                continue
            self._check_fail_logs(line)
            self._check_match_logs(line)

        logger.info("Matches found: {}".format(self._matches))
        return self._matches

    def validate(self, wait=None, message="waiting for log validation", **kwargs):
        """Validate log pattern

        Args:
            wait: Wait for log validation (timeout)
            message: Specific message.
        Returns (bool): True if expected pattern matched in log else False
        Raise:
            TimedOutError: If failed to match pattern in respective timeout
            FailPatternMatchError: If failure pattern matched
        """

        if wait:
            wait_for(lambda: self._is_valid, delay=5, timeout=wait, message=message, **kwargs)
            return True
        else:
            return self._is_valid

    @contextmanager
    def waiting(self, **kwargs):
        self.start_monitoring()
        yield
        self.validate(**kwargs)
