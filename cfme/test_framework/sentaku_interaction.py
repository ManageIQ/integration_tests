"""use_context(*contexts, **kw): wrap the test into appliance.contet.use(*contexts)
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    marker = item.get_marker("use_context")
    appliance = item.funcargs.get('appliance')

    if marker is None:
        yield
    elif appliance is None:
        yield
        # warn
    else:
        collected_contexts = []
        for item in marker.args:
            if isinstance(type, item):
                collected_contexts.append(item)
            else:
                collected_contexts.extend(item)

        with appliance.context.use(*collected_contexts, **marker.kwargs):
            yield
