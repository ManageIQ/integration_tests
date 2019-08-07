"""
To use merkyl you have to configure artifactor in conf/env.local.yaml
and you have to open port 8291 for you appliance. Here you can see an
example of artifactor configuration:

        artifactor:
          per_run: run
          plugins:
            filedump:
              enabled: true
              plugin: filedump
            logger:
              enabled: true
              level: DEBUG
              plugin: logger
            merkyl:
              enabled: true
              log_files:
                # - /var/www/miq/vmdb/log/evm.log
                # You can put file name here, if you want it open
                # for whole session and not just test duration.
                # For that you also have to use setup_merkyl fixture.
              plugin: merkyl
              port: 8192
            reporter:
              enabled: true
              only_failed: false
              plugin: reporter
            softassert:
              enabled: true
              plugin: softassert
          reuse_dir: true
          server_address: 127.0.0.1
          server_enabled: true
          squash_exceptions: true
          threaded: false
"""
import attr
import pytest

from cfme.fixtures.artifactor_plugin import fire_art_test_hook


@attr.s
class MerkylInspector(object):
    """ A simple adapter to aid in Merkyl Log Inspection during a test.

    This class is really only useful during a test and is designed to abstract
    away accessing the request object. The hooks which are fired can be done
    so during the test without this class/fixture, this is merely a convenience
    and does nothing special.
    """

    node = attr.ib()
    ip = attr.ib()

    def get_log(self, log_name):
        """ A simple getter for log files.

        Returns the cached content of a particular log

        Args:
            log_name: Full path to the log file wishing to be received.
        """
        res = fire_art_test_hook(
            self.node, 'get_log_merkyl', ip=self.ip,
            filename=log_name, grab_result=True)
        return res.get('merkyl_content', '')

    def add_log(self, log_name):
        """ Adds a log file to the merkyl process.

        This function adds a log file path to the merkyl process on the
        appliance. This is relevant only for the duration of the test. At
        the end of the test, the file is removed from the merkyl tracker.

        Note that this is a blocking call, ie, we ensure that the file
        is being logged by merkyl, before we continue. This is important
        and prevents the file_add operation being queued and processes
        which generate log information activating before the log is being
        monitored. This is achieved using the grab_result switch, but
        in fact, nothing will be received.

        It is worth noting that the file path must be "discoverable" by merkyl.
        This may mean editing the allowed_files prior to deploying merkyl.

        Args:
            log_name: Full path to the log file wishing to be monitored.

        """
        fire_art_test_hook(
            self.node, 'add_log_merkyl', ip=self.ip,
            filename=log_name, grab_result=True)

    def reset_log(self, log_name):
        """ Resets log

        This function clears content of a log file that merkyl is tailing.
        Note that file stays open and merkyl keeps tailing it.

        Args:
            log_name: Full path to the log file that you want to reset
        """
        fire_art_test_hook(
            self.node, 'reset_log_merkyl', ip=self.ip,
            filename=log_name, grab_result=True)

    def search_log(self, needle, log_name):
        """ A simple search, test if needle is in cached log_contents.

        Does a simple search of needle in contents, needle can be used as string
        or regular expression. Note that this does not trawl the previous
        contents of the file, but only looks at the log information which has
        been gathered since merkyl was tracking the file.

        Args:
            needle: String or compiled regular expression

        Simple example using needle as regex and re.MULTILINE flag:
            merkyl_inspector.search_log(re.compile(r'^simple multiline regex$',
                                                   re.MULTILINE),
                                        path/to/log/name.log)
        """
        contents = self.get_log(log_name)
        if isinstance(needle, str):
            return needle in contents
        else:
            return bool(needle.search(contents))


@pytest.fixture(scope='function')
def merkyl_inspector(request, appliance):
    """ Provides a MerkylInspector instance.

    This fixture is used to gain access to a relevant MerkylInspector instance.

    Example usage is below:

    .. code-block:: python

        def test_test(merkyl_inspector):
            merkyl_inspector.add_log('/path/to/log/file')
            # Do something
            if merkyl_inspector.search_log('needle', '/path/to/log/file'):
                print(merkyl_inspector.get_log('/path/to/log/file'))
    """
    return MerkylInspector(node=request.node, ip=appliance.hostname)
