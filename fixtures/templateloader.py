# -*- coding: utf-8 -*-
"""Preloads all templates on all providers that were selected for testing. Useful for test collect.
"""
import pytest

from fixtures.prov_filter import filtered
from fixtures.pytest_store import store, write_line
from utils import trackerbot

TEMPLATES = {}


@pytest.mark.trylast
def pytest_sessionstart(session):
    if store.parallelizer_role == 'master':
        return
    write_line("Loading templates from trackerbot")
    provider_templates = trackerbot.provider_templates(trackerbot.api())
    for provider in filtered.providers:
        TEMPLATES[provider] = provider_templates.get(provider, [])
