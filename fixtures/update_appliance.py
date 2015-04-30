"""Appliance update plugin

If update_urls is set in the env, re-trigger the update_rhel configuration
step to update the appliance with the new URLs

"""
import os

import pytest


def pytest_parallel_configured():
    if pytest.store.parallelizer_role != 'master' and 'update_urls' in os.environ:
        pytest.store.write_line('updating appliance before testing')
        pytest.store.current_appliance.update_rhel(*str(os.environ['update_urls']).split())
