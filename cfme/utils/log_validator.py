import re

import pytest
from _pytest.outcomes import Failed

from .ssh import SSHTail
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


class LogValidator(object):
    """
    Log content validator class provides methods
    to fix the log content before test is started,
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
          evm_tail.fix_before_start()
          evm_tail.validate_logs()
    """

    def __init__(self, remote_filename, **kwargs):
        self.skip_patterns = kwargs.pop('skip_patterns', [])
        self.failure_patterns = kwargs.pop('failure_patterns', [])
        self.matched_patterns = kwargs.pop('matched_patterns', [])

        self._remote_file_tail = SSHTail(remote_filename, **kwargs)
        self.matches = {key: 0 for key in self.matched_patterns}

    def fix_before_start(self):
        """Start monitoring log before action"""
        self._remote_file_tail.set_initial_file_end()

    def _validation(self):
        for line in self._remote_file_tail:
            if self._check_skip_logs(line):
                continue
            self._check_fail_logs(line)
            self._check_match_logs(line)
        logger.info("Matches found: {}".format(self.matches))

    def _check_skip_logs(self, line):
        for pattern in self.skip_patterns:
            if re.search(pattern, line):
                logger.info('Skip pattern {} was matched on line {},\
                            so skipping this line'.format(pattern, line))
                return True
        return False

    def _check_fail_logs(self, line):
        for pattern in self.failure_patterns:
            if re.search(pattern, line):
                pytest.fail('Failure pattern {} was matched on line {}'.format(pattern, line))

    def _check_match_logs(self, line):
        for pattern in self.matched_patterns:
            if re.search(pattern, line):
                logger.info('Expected pattern {} was matched on line {}'.format(pattern, line))
                self.matches[pattern] = self.matches[pattern] + 1

    def validate_logs(self):
        """Validate log pattern"""
        self._validation()
        for pattern, count in self.matches.items():
            if count == 0:
                pytest.fail(
                    'Expected pattern {} did not match; match count {}'.format(pattern, count)
                )

    @property
    def patterns_match_count(self):
        """It will return pattern match count dictionary"""
        self._validation()
        return self.matches

    def wait_for_log_validation(
            self, delay=5, num_sec=180, message="waiting for log validation", **kwargs
    ):
        """ Wait for log validation, takes the kwargs as wait_for. This function will reduce
            duplicate functions in tests that wait_for log_validation. It is necessary to create
            this function since _verify_match_logs raise pytest.fail() when it fails to find the
            match pattern in the logs.

            Note that you must call fix_before_start() before making use of this function.
        """
        def validate():
            try:
                self.validate_logs()
                return True
            except Failed:
                return False
        wait_for(validate, delay=delay, num_sec=num_sec, message=message, **kwargs)

    def wait_for_expected_patterns_match_count(
        self,
        expected_match,
        timeout=180,
        delay=5,
        message="Check for expected match count",
        **kwargs
    ):
        """ wait for expected match count found in respective log file.

        Args:
            expected_match (dir): expected patterns match count
            timeout (int): timeout
            delay (int): delay time
            message (str): wait_for message
        """

        def _match():
            return set(self.patterns_match_count) == set(expected_match)

        wait_for(_match, timeout=timeout, message=message, delay=delay, **kwargs)
