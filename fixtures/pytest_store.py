"""Storage for pytest objects during test runs

The objects in the module will change during the course of a test run,
so they have been stashed into the 'store' namespace

Usage:

    from fixtures.pytest_store import store
    # store.config, store.pluginmanager, store.session

The availability of these objects varies during a test run, but
all should be available in the collection and testing phases of a test run.

"""
import sys
from urlparse import urlparse

from _pytest.terminal import TerminalReporter
from py.io import TerminalWriter

from utils import property_or_none
from utils import conf


class FlexibleTerminalReporter(TerminalReporter):
    """A TerminalReporter stand-in that pretends to work even without a py.test config."""
    def __init__(self, config=None, file=None):
        if config:
            # If we have a config, nothing more needs to be done
            return TerminalReporter.__init__(self, config, file)

        # Without a config, pretend to be a TerminalReporter
        # hook-related functions (logreport, collection, etc) will be outrigt broken,
        # but the line writers should still be usable
        if file is None:
            file = sys.stdout

        self._tw = self.writer = TerminalWriter(file)
        self.hasmarkup = self._tw.hasmarkup
        self.reportchars = ''
        self.currentfspath = None


class Store(object):
    """pytest object store

    If a property isn't available for any reason (including being accessed outside of a pytest run),
    it will be None.

    """
    def __init__(self):
        self.config = None
        self.session = None
        self._current_appliance = []

    @property
    def current_appliance(self):
        if not self._current_appliance:
            from utils.appliance import IPAppliance
            self._current_appliance.append(IPAppliance(urlparse(self.base_url).netloc))
        return self._current_appliance[-1]

    @property
    def base_url(self):
        """ If there is a current appliance the base url of that appliance is returned
            else, the base_url from the config is returned."""

        if self._current_appliance:
            return self._current_appliance[-1].url
        else:
            return conf.env['base_url']

    @property
    def in_pytest_session(self):
        return self.session is not None

    @property_or_none
    def fixturemanager(self):
        # "publicize" the fixturemanager
        return self.session._fixturemanager

    @property_or_none
    def capturemanager(self):
        return self.pluginmanager.getplugin('capturemanager')

    @property_or_none
    def pluginmanager(self):
        # Expose this directly on the store for convenience in getting/setting plugins
        return self.config.pluginmanager

    @property_or_none
    def terminalreporter(self):
        if self.pluginmanager is not None:
            reporter = self.pluginmanager.getplugin('terminalreporter')
            if reporter:
                return reporter

        return FlexibleTerminalReporter(self.config)

    @property_or_none
    def terminaldistreporter(self):
        if self.pluginmanager is not None:
            reporter = self.pluginmanager.getplugin('terminaldistreporter')
            if reporter:
                return reporter

    @property_or_none
    def slave_manager(self):
        return self.pluginmanager.getplugin('slave_manager')


store = Store()


def _push_appliance(app):
    store._current_appliance.append(app)
    if app.browser_steal:
        from utils import browser
        browser.start()


def _pop_appliance(app):
    store._current_appliance.pop()
    if app.browser_steal:
        from utils import browser
        browser.start()


def pytest_configure(config):
    store.config = config


def pytest_sessionstart(session):
    store.session = session
