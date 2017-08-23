"""Fixtures specifically for performance tests."""
from cfme.utils.perf import set_rails_loglevel
from cfme.utils.perf import get_worker_pid
import pytest


@pytest.yield_fixture(scope='session')
def cfme_log_level_rails_debug():
    set_rails_loglevel('debug')
    yield
    set_rails_loglevel('info')


@pytest.yield_fixture(scope='module')
def ui_worker_pid():
    yield get_worker_pid('MiqUiWorker')
