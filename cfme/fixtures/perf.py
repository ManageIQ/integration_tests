"""Fixtures specifically for performance tests."""
import pytest

from cfme.utils.perf import get_worker_pid
from cfme.utils.perf import set_rails_loglevel


@pytest.fixture(scope='session')
def cfme_log_level_rails_debug():
    set_rails_loglevel('debug')
    yield
    set_rails_loglevel('info')


@pytest.fixture(scope='module')
def ui_worker_pid():
    yield get_worker_pid('MiqUiWorker')
