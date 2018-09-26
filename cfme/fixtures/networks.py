import pytest
from argparse import Namespace
from contextlib import contextmanager

from cfme.exceptions import NeedleNotFoundInLog
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for, TimedOutError


@pytest.fixture
def targeted_refresh():
    """
    This fixture tests whether targeted refresh was triggered for given targets.
    It basically tails evm.log to see whether a line like this has occured:

    ```
    [Collection of targets with id: [{:ems_ref=>"b35d3afe-6f19-4da8-b1ee-b79de433cace"}, ... ]]
    ```
    for each target and raises an error if not.

    Usage:

        def test_something(targeted_refresh)
                trigger_targeted_refresh() <- some function that will trigger
                                              targeted refresh
                with targeted_refresh.target_timeout():
                    targeted_refresh.register_target('ref-123456', 'Subnet named TEST')
                    targeted_refresh.register_target('ref-aaaabb', 'Router named TEST')
    """
    needle_template = r'^.*Collection of targets with id.*:ems_ref=>"{}".*$'
    targets = {}  # { needle: comment }
    log_validator = LogValidator('/var/www/miq/vmdb/log/evm.log')
    log_validator.fix_before_start()

    def check_log():
        logger.info('Looking for %s needles in evm.log: %s', len(targets), list(targets.values()))
        log_validator.update_matched_patterns(list(targets))
        for revealed_pattern in log_validator.validate_logs(auto_fail=False):
            logger.info('Found needle %s', targets.pop(revealed_pattern))
        return len(targets) == 0

    @contextmanager
    def timeout():
        yield

        try:
            wait_for(check_log, delay=5, num_sec=60)
        except TimedOutError:
            raise NeedleNotFoundInLog('Targeted refresh did not trigger for:\n{}'.format(
                                      ',\n'.join(map(lambda t: '- ' + t, targets.values()))))

    def register_target(ems_ref, comment):
        targets[needle_template.format(ems_ref)] = comment

    yield Namespace(register_target=register_target, timeout=timeout)
