"""fixtureconf: Marker for passing args and kwargs to test fixtures

Positional and keyword arguments to this marker will be stored on test items
in the _fixtureconf attribute (dict). kwargs will be stored as-is, the args
tuple will be packed into the dict under the 'args' key.

Use the "fixtureconf" fixture in tests to easily access the fixtureconf dict
"""


def pytest_configure(config):
    config.addinivalue_line('markers', __doc__)


def pytest_runtest_setup(item):
    fixtureconf_mark = item.keywords.get('fixtureconf')
    args = getattr(fixtureconf_mark, 'args', tuple())
    kwargs = getattr(fixtureconf_mark, 'kwargs', dict())
    fixtureconf = dict()
    fixtureconf['args'] = args
    fixtureconf.update(kwargs)
    # "item" becomes "request.node" in fixtures down the line
    # remember to use the request fixture in fixture funcargs
    item._fixtureconf = fixtureconf
