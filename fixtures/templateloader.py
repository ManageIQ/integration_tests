# -*- coding: utf-8 -*-
"""Preloads all templates on all providers that were selected for testing. Useful for test collect.
"""
from __future__ import unicode_literals
from fixtures.prov_filter import filtered
from fixtures.pytest_store import store, write_line
from utils import trackerbot

TEMPLATES = {}


def pytest_configure():
    if store.parallelizer_role == 'master' or 'url' not in trackerbot.conf:
        return

    write_line("Loading templates from trackerbot")
    provider_templates = trackerbot.provider_templates(trackerbot.api())
    for provider in filtered.providers:
        TEMPLATES[provider] = provider_templates.get(provider, [])
