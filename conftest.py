"""
Top-level conftest.py just configures pytest assertion rewriting
and adds the framework pytest plugin to pytest
"""

import pytest
pytest.register_assert_rewrite(
    'markers',
    'fixtures.pytest_store'
    'fixtures.artifactor_plugin',
    'cfme.fixtures.rdb',
    'fixtures',
    'fixtures.pytest_store',
    'fixtures.templateloader',
    'fixtures.terminalreporter',
    'fixtures.ui_coverage',
    'markers.polarion',
    'cfme.fixtures.pytest_selenium',
)

pytest_plugins = ['cfme.test_framework.pytest_plugin']
