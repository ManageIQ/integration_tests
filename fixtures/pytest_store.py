"""Storage for pytest objects during test runs

The objects in the module will change during the course of a test run,
so they have been stashed into the 'store' namespace

Usage:

    from fixtures.pytest_store import store
    # store.config, store.pluginmanager, store.session

The availability of these objects varies during a test run, but
all should be available in the collection and testing phases of a test run.

"""


class Store(object):
    def __init__(self):
        self.config = None
        self.session = None

    @property
    def fixturemanager(self):
        # "publicize" the fixturemanager
        try:
            return self.session._fixturemanager
        except AttributeError:
            return None

    @property
    def pluginmanager(self):
        # Expose this directly on the store for convenience in getting/setting plugins
        try:
            return self.config.pluginmanager
        except AttributeError:
            return None

store = Store()


def pytest_configure(config):
    store.config = config


def pytest_sessionstart(session):
    store.session = session
