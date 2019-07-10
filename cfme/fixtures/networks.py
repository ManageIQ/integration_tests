import re
from argparse import Namespace
from contextlib import contextmanager

import pytest

from cfme.exceptions import NeedleNotFoundInLog
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


@pytest.fixture
def targeted_refresh(merkyl_setup, merkyl_inspector):
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
    evm_log = '/var/www/miq/vmdb/log/evm.log'
    needle_template = r'^.*Collection of targets with id.*:ems_ref=>"{}".*$'
    merkyl_inspector.add_log(evm_log)
    merkyl_inspector.reset_log(evm_log)
    targets = set()  # { (ems_ref, comment), (ems_ref, comment), ... }

    def check_log():
        logger.info('Looking for %s needles in evm.log: %s', len(targets), [t[1] for t in targets])
        content = merkyl_inspector.get_log(evm_log)
        for target in set(targets):
            if target[0].search(content):
                logger.info('Found needle %s', target[1])
                targets.remove(target)
        return len(targets) == 0

    @contextmanager
    def timeout():
        yield

        try:
            wait_for(check_log, delay=5, num_sec=60)
        except TimedOutError:
            raise NeedleNotFoundInLog('Targeted refresh did not trigger for:\n{}'.format(
                                      ',\n'.join(['- ' + t[1] for t in targets])))

    def register_target(ems_ref, comment):
        targets.add((re.compile(needle_template.format(ems_ref), re.MULTILINE), comment))

    yield Namespace(register_target=register_target, timeout=timeout)
