# -*- coding: utf-8 -*-
"""This module allows you to update an appliance with latest RHEL.

It has two uses:
1) If only ``--update-appliance`` is specified, it will use the YAML url.
2) If you also specify one or more ``--update-url``, it will use them instead.
"""
from cfme.fixtures.pytest_store import store


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption(
        '--update-appliance',
        dest='update_appliance', action='store_true', default=False,
        help="Enable updating an appliance before the first test is run.")
    group.addoption(
        '--update-url',
        dest='update_urls', action='append', default=[],
        help="URLs to update with. If none are passed, yaml key is used.")


def pytest_sessionstart(session):
    if store.parallelizer_role == 'master':
        return
    if not session.config.getoption("update_appliance"):
        return
    store.write_line("Initiating appliance update ...")
    urls = session.config.getoption("update_urls")
    store.current_appliance.update_rhel(*urls, reboot=True)
    store.write_line("Appliance update finished, waiting for UI ...")
    store.current_appliance.wait_for_web_ui()
    store.write_line("Appliance update finished ...")
