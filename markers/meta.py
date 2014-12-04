# -*- coding: utf-8 -*-
"""meta(\*\*metadata): Marker for metadata addition"""
import pytest


class metadict(dict):
    """A dictionary that can access items as object variables, returns None if not found"""
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            return None


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


@pytest.mark.tryfirst
def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item._metadata = metadict()
        meta = item.get_marker("meta")
        if meta is None:
            continue
        metas = reversed([x.kwargs for x in meta])  # Extract the kwargs, reverse the order
        for meta in metas:
            item._metadata.update(meta)


@pytest.fixture(scope="function")
def meta(request):
    return request.node._metadata
