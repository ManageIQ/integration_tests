"""Storage for pytest objects during test runs

The objects in the module will change during the course of a test run,
so they have been stashed into the 'store' namespace

Usage:

    # imported directly (store is pytest.store)
    from cfme.fixtures.pytest_store import store
    store.config, store.pluginmanager, store.session

The availability of these objects varies during a test run, but
all should be available in the collection and testing phases of a test run.

"""
import os
import sys

import fauxfactory
from _pytest.terminal import TerminalReporter
from cached_property import cached_property
from py.io import TerminalWriter

from cfme.utils import diaper


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

    @property
    def current_appliance(self):
        # layz import due to loops and loops and loops
        from cfme.utils import appliance
        # TODO: concieve a better way to detect/log import-time missuse
        # assert self.config is not None, 'current appliance not in scope'
        return appliance.current_appliance

    def __init__(self):
        #: The py.test config instance, None if not in py.test
        self.config = None

        #: The current py.test session, None if not in a py.test session
        self.session = None

        #: Parallelizer role, None if not running a parallelized session
        self.parallelizer_role = None

        # Stash of the "real" terminal reporter once we get it,
        # so we don't have to keep going through pluginmanager
        self._terminalreporter = None
        #: hack variable until we get a more sustainable solution
        self.ssh_clients_to_close = []

        self.uncollection_stats = {}

    @property
    def has_config(self):
        return self.config is not None

    def _maybe_get_plugin(self, name):
        """ returns the plugin if the pluginmanager is availiable and the plugin exists"""
        return self.pluginmanager and self.pluginmanager.getplugin(name)

    @property
    def in_pytest_session(self):
        return self.session is not None

    @property
    def fixturemanager(self):
        # "publicize" the fixturemanager
        return self.session and self.session._fixturemanager

    @property
    def capturemanager(self):
        return self._maybe_get_plugin('capturemanager')

    @property
    def pluginmanager(self):
        # Expose this directly on the store for convenience in getting/setting plugins
        return self.config and self.config.pluginmanager

    @property
    def terminalreporter(self):
        if self._terminalreporter is not None:
            return self._terminalreporter

        reporter = self._maybe_get_plugin('terminalreporter')
        if reporter and isinstance(reporter, TerminalReporter):
            self._terminalreporter = reporter
            return reporter

        return FlexibleTerminalReporter(self.config)

    @property
    def terminaldistreporter(self):
        return self._maybe_get_plugin('terminaldistreporter')

    @property
    def parallel_session(self):
        return self._maybe_get_plugin('parallel_session')

    @property
    def slave_manager(self):
        return self._maybe_get_plugin('slave_manager')

    @property
    def slaveid(self):
        return getattr(self.slave_manager, 'slaveid', None)

    @cached_property
    def my_ip_address(self):
        """Make a few guesses at what the pytest host's address is
        Last guess defaulting to localhost
        """
        try:
            # Check the environment first
            env_or_ssh = os.environ.get(
                'CFME_MY_IP_ADDRESS',
                self.current_appliance.ssh_client.client_address
            )
            return env_or_ssh or '127.0.0.1'
        except KeyError:
            # Fall back to having an appliance tell us what it thinks our IP
            # address is
            return

    def write_line(self, line, **kwargs):
        return write_line(line, **kwargs)


store = Store()


def pytest_namespace():
    # Expose the pytest store as pytest.store
    return {'store': store}


def pytest_plugin_registered(manager):
    # config will be set at the second call to this hook
    if store.config is None:
        store.config = manager.getplugin('pytestconfig')


def pytest_sessionstart(session):
    store.session = session


def write_line(line, **kwargs):
    """A write-line helper that should *always* write a line to the terminal

    It knows all of py.tests dirty tricks, including ones that we made, and works around them.

    Args:
        **kwargs: Normal kwargs for pytest line formatting, stripped from slave messages

    """
    if store.slave_manager:
        # We're a pytest slave! Write out the vnc info through the slave manager
        store.slave_manager.message(line, **kwargs)
    else:
        # If py.test is supressing stdout/err, turn that off for a moment
        with diaper:
            store.capturemanager.suspendcapture()

        # terminal reporter knows whether or not to write a newline based on currentfspath
        # so stash it, then use rewrite to blow away the line that printed the current
        # test name, then clear currentfspath so the test name is reprinted with the
        # write_ensure_prefix call. shenanigans!
        cfp = store.terminalreporter.currentfspath
        # carriage return, write spaces for the whole line, carriage return, write the new line
        store.terminalreporter.line('\r' + ' ' * store.terminalreporter._tw.fullwidth + '\r' + line,
            **kwargs)
        store.terminalreporter.currentfspath = fauxfactory.gen_alphanumeric(8)
        store.terminalreporter.write_ensure_prefix(cfp)

        # resume capturing
        with diaper:
            store.capturemanager.resumecapture()
