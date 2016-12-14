import re
import pytest

from ssh import SSHTail
from utils.log import logger


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
        self._remote_file_tail = SSHTail(remote_filename)
        self.skip_patterns = kwargs['skip_patterns'] if 'skip_patterns' in kwargs else []
        self.failure_patterns = kwargs['failure_patterns'] if 'failure_patterns' in kwargs else []
        self.matched_patterns = kwargs['matched_patterns'] if 'matched_patterns' in kwargs else []
        self.matches = {}

    def fix_before_start(self):
        self._remote_file_tail.set_initial_file_end()

    def validate_logs(self):
        for line in self._remote_file_tail:
            if self._check_skip_logs(line):
                continue
            self._check_fail_logs(line)
            self._check_match_logs(line)
        self._verify_match_logs()

    def _check_skip_logs(self, line):
        for pattern in self.skip_patterns:
            if re.match(pattern, line):
                logger.info('Skip pattern {} was matched on line {},\
                            so skipping this line'.format(pattern, line))
                return True
        return False

    def _check_fail_logs(self, line):
        for pattern in self.failure_patterns:
            if re.match(pattern, line):
                pytest.fail('Failure pattern {} was matched on line {}'.format(pattern, line))

    def _check_match_logs(self, line):
        for pattern in self.matched_patterns:
            if re.match(pattern, line):
                logger.info('Expected pattern {} was matched on line {}'.format(pattern, line))
                self.matches[pattern] = True

    def _verify_match_logs(self):
        for pattern in self.matched_patterns:
            if not self.matches[pattern]:
                pytest.fail('Expected pattern {} did not match'.format(pattern))
