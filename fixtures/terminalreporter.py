import sys

from _pytest.terminal import TerminalReporter
from py.io import TerminalWriter


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


def reporter(config=None):
    if config:
        reporter = config.pluginmanager.getplugin('terminalreporter')
        if reporter:
            return reporter

    return FlexibleTerminalReporter(config)
