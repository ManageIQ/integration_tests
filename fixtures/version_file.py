from __future__ import unicode_literals
import pytest

from utils.path import log_path


def pytest_sessionstart():
    if pytest.store.parallelizer_role != 'slave':
        with log_path.join('appliance_version').open('w') as appliance_version:
            appliance_version.write(pytest.store.current_appliance.version.vstring)
