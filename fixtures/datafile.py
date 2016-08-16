from __future__ import unicode_literals
import os

import pytest

from fixtures.terminalreporter import reporter
from utils.datafile import data_path_for_filename, load_data_file
from utils.path import data_path, log_path

# Collection for storing unique combinations of data file paths
# and filenames for usage reporting after a completed test run
seen_data_files = set()


@pytest.fixture(scope="module")
def datafile(request):
    """datafile(filename, replacements)
    datafile fixture, with templating support

    Args:

        filename: filename to load from the data dir
        replacements: template replacements

    Returns: Path to the loaded datafile

    Usage:

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

    .. rubric:: Templates:

    This fixture can also handle template replacements. If the datafile
    being loaded is a python template, the dictionary of replacements
    can be passed as the 'replacements' keyword argument. In this case,
    the returned data file will be a NamedTemporaryFile prepopulated
    with the interpolated result from combining the template with
    the replacements mapping.

    * http://docs.python.org/2/library/string.html#template-strings
    * http://docs.python.org/2/library/tempfile.html#tempfile.NamedTemporaryFile

    """
    return _FixtureDataFile(request)


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--udf-report', action='store_true', default=False,
        dest='udf_report',
        help='flag to generate an unused data files report')


def pytest_sessionfinish(session, exitstatus):
    udf_log_file = log_path.join('unused_data_files.log')

    if udf_log_file.check():
        # Clean up old udf log if it exists
        udf_log_file.remove()

    if session.config.option.udf_report is False:
        # Short out here if not making a report
        return

    # Output an unused data files log after a test run
    data_files = set()
    for dirpath, dirnames, filenames in os.walk(str(data_path)):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            data_files.add(filepath)
    unused_data_files = data_files - seen_data_files

    if unused_data_files:
        # Write the log of unused data files out, minus the data dir prefix
        udf_log = ''.join(
            (line[len(str(data_path)):] + '\n' for line in unused_data_files)
        )
        udf_log_file.write(udf_log + '\n')

        # Throw a notice into the terminal reporter to check the log
        tr = reporter()
        tr.write_line('')
        tr.write_sep(
            '-',
            '%d unused data files after test run, check %s' % (
                len(unused_data_files), udf_log_file.basename
            )
        )


class _FixtureDataFile(object):
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
