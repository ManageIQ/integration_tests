import os

import pytest

from utils.datafile import *

# Collection for storing unique combinations of data file paths
# and filenames for usage reporting after a completed test run
seen_data_files = set()

@pytest.fixture(scope="module")
def datafile(request):
    """datafile fixture, with templating support

    Usage
    =====

    Given a filename, it will attempt to open the given file from the
    test's corresponding data dir. For example, this:

        datafile('testfile') # in tests/subdir/test_module_name.py

    Would return a file object representing this file:

        /path/to/cfme_tests/data/subdir/test_module_name/testfile

    Given a filename with a leading slash, it will attempt to load the file
    relative to the root of the data dir. For example, this:

        datafile('/common/testfile') # in tests/subdir/test_module_name.py

    Would return a file object representing this file:

        /path/to/cfme_tests/data/common/testfile

    Note that the test module name is not used with the leading slash.

    Templates
    =========

    This fixture can also handle template replacements. If the datafile
    being loaded is a python template[1], the dictionary of replacements
    can be passed as the 'replacements' keyword argument. In this case,
    the returned data file will be a NamedTemporaryFile[2] prepopulated
    with the interpolated result from combining the template with
    the replacements mapping.

    [1]: http://docs.python.org/2/library/string.html#template-strings
    [2]: http://docs.python.org/2/library/tempfile.html#tempfile.NamedTemporaryFile

    """
    return FixtureDataFile(request)

def pytest_sessionfinish(session, exitstatus):
    # Output an unused data files log after a test run
    data_path = os.path.join(str(session.fspath), 'data/')
    data_files = set()
    for dirpath, dirnames, filenames in os.walk(data_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            data_files.add(filepath)
    unused_data_files = data_files - seen_data_files

    udf_log_file_name = 'unused_data_files.log'
    udf_log_file = session.fspath.join(udf_log_file_name)
    if unused_data_files:
        # Write the log of unused data files out, minus the data dir prefix
        udf_log = ''.join(
            (line[len(data_path):] + '\n' for line in unused_data_files)
        )
        udf_log_file.write(udf_log + '\n')

        # Throw a notice into the terminal reporter to check the log
        reporter = session.config.pluginmanager.getplugin('terminalreporter')
        reporter.write_line('')
        reporter.write_sep(
            '-',
            '%d unused data files after test run, check %s' % (
                len(unused_data_files), udf_log_file_name
            )
        )
    elif udf_log_file.check():
        # Clean up old udf log if it exists
        udf_log_file.remove()


class FixtureDataFile(object):
    def __init__(self, request):
        self.base_path = str(request.session.fspath)
        self.testmod_path = str(request.fspath)

    def __call__(self, filename, replacements=None):
        if filename.startswith('/'):
            complete_path = data_path_for_filename(
                filename.strip('/'), self.base_path)
        else:
            complete_path = data_path_for_filename(
                filename, self.base_path, self.testmod_path)

        seen_data_files.add(complete_path)

        return load_data_file(complete_path, replacements)
