# -*- coding: utf-8 -*-
"""Preloads all templates on all providers that were selected for testing. Useful for test collect.
"""
import pytest

from fixtures.prov_filter import filtered
from fixtures.pytest_store import write_line
from utils.providers import provider_factory

TEMPLATES = {}


@pytest.mark.trylast
def pytest_configure(config):
    write_line("Loading templates from providers (this may take some time)")
    for provider in filtered.providers:
        try:
            p = provider_factory(provider)
            TEMPLATES[provider] = set(map(str, p.list_template()))
        except Exception as e:
            write_line("-> Error: {}({})\n".format(type(e).__name__, str(e)), red=True)
            TEMPLATES[provider] = None
    write_line("Template retrieval finished")
