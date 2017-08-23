# -*- coding: utf-8 -*-
"""Preloads all templates on all providers that were selected for testing. Useful for test collect.
"""
import pytest
from fixtures.pytest_store import store
from cfme.utils import trackerbot
from cfme.utils.providers import list_provider_keys

TEMPLATES = {}


@pytest.mark.tryfirst
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.addoption("--use-template-cache", dest="use_template_cache", action="store_true",
        default=False, help="Use a cached version of the templates and not redownload them")


def pytest_configure(config):
    if store.parallelizer_role == 'master' or trackerbot.conf.get('url') is None:
        return

    # A further optimization here is to make the calls to trackerbot per provider
    # and perhaps only pull the providers that are needed, however that will need
    # to ensure that the tests that just randomly use providers adhere to the filters
    # which may be too tricky right now.

    count = 0

    if not config.getoption('use_template_cache'):
        store.terminalreporter.line("Loading templates from trackerbot...", green=True)
        provider_templates = trackerbot.provider_templates(trackerbot.api())
        for provider in list_provider_keys():
            TEMPLATES[provider] = provider_templates.get(provider, [])
            config.cache.set('miq-trackerbot/{}'.format(provider), TEMPLATES[provider])
            count += len(TEMPLATES[provider])
    else:
        store.terminalreporter.line("Using templates from cache...", green=True)
        provider_templates = None
        for provider in list_provider_keys():
            templates = config.cache.get('miq-trackerbot/{}'.format(provider), None)
            if templates is None:
                store.terminalreporter.line(
                    "Loading templates for {} from source as not in cache".format(
                        provider), green=True)
                if not provider_templates:
                    provider_templates = trackerbot.provider_templates(trackerbot.api())
                templates = provider_templates.get(provider, [])
                config.cache.set('miq-trackerbot/{}'.format(provider), templates)
            count += len(templates)
            TEMPLATES[provider] = templates
    store.terminalreporter.line("  Loaded {} templates successfully!".format(count), green=True)
