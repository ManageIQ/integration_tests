import pytest

from fixtures.artifactor_plugin import appliance_ip_address, art_client, get_test_idents


class MerkylInspector(object):
    def __init__(self, request):
        """ A simple adapter to aid in Merkyl Log Inspection during a test.

        This class is really only useful during a test and is designed to abstract
        away accessing the request object. The hooks which are fired can be done
        so during the test without this class/fixture, this is merely a convenience
        and does nothing special.
        """
        name, location = get_test_idents(request.node)
        self.test_name = name
        self.test_location = location
        self.ip = appliance_ip_address

    def get_log(self, log_name):
        """ A simple getter for log files.

        Returns the cached content of a particular log

        Args:
            log_name: Full path to the log file wishing to be received.
        """
        res = art_client.fire_hook('get_log_merkyl', test_name=self.test_name,
                                   test_location=self.test_location, ip=self.ip,
                                   filename=log_name, grab_result=True)
        return res['merkyl_content']

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
        art_client.fire_hook('add_log_merkyl', test_name=self.test_name,
                             test_location=self.test_location, ip=self.ip,
                             filename=log_name, grab_result=True)

    def search_log(self, needle, log_name):
        """ A simple search, test if needle is in cached log_contents.

        Does a simple search of needle in contents. Note that this does not
        trawl the previous contents of the file, but only looks at the log
        information which has been gathered since merkyl was tracking the file.
        """
        contents = self.get_log(log_name)
        if needle in contents:
            return True
        else:
            return False


@pytest.fixture(scope='function')
def merkyl_inspector(request):
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
    return MerkylInspector(request)
