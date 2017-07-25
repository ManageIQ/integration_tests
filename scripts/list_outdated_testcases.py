#!/usr/bin/env python

# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Compare output of 'pytest --collect-only' with data in Polarion.

The outcome is a CSV file with test cases that might need to be
deactivated/deleted in Polarion.

Usage:
    Export a CSV file with _automated_ test cases from Polarion and use it as
    an input for this script.

IMPORTANT: double-check that the test case is really missing in pytest and was
not just uncollected because of provider type, appliance version, etc.
"""

from __future__ import unicode_literals, absolute_import

import argparse
import codecs
import csv
import logging
import operator
import os
import re
import sys

from cStringIO import StringIO
from contextlib import contextmanager

from dump2polarion.csvtools import get_imported_data


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


class CompareException(Exception):
    """testcases exception."""


# pylint: disable=too-few-public-methods
class UnicodeWriter(object):
    """A CSV writer that writes rows to CSV file "f" encoded in the given encoding"""

    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        """writerow wrapper"""
        self.writer.writerow([s.encode('utf-8') for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode('utf-8')
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)


def _get_args(args=None):
    """Get command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file', required=True,
                        help='Input CSV file exported from Polarion')
    parser.add_argument('-o', '--output_file', required=True,
                        help='Output CSV file with outdated test cases')
    return parser.parse_args(args)


def _check_environment():
    # check that launched in integration tests repo
    if not os.path.exists('cfme/tests'):
        raise CompareException('Not running in the integration tests repo')
    # check that running in virtualenv
    if not hasattr(sys, 'real_prefix'):
        raise CompareException('Not running in virtual environment')


@contextmanager
def _redirect_output(out):
    new_target = out
    old_target, sys.stdout = sys.stdout, new_target
    old_log_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.ERROR)
    try:
        yield new_target
    finally:
        sys.stdout = old_target
        logging.getLogger().setLevel(old_log_level)


def _run_pytest():
    """Runs the pytest command."""
    pytest_retval = None
    _check_environment()

    args = [
        '--collect-only',
        '--perf',
        '--long-running',
        '--use-provider', 'complete'
    ]

    import pytest
    logger.info('Generating list of test cases using `pytest {}`'.format(' '.join(args)))
    output = StringIO()
    with _redirect_output(output):
        pytest_retval = pytest.main(args)

    if not output or pytest_retval != 0:
        raise CompareException('The list of test cases was not generated')

    return output.getvalue().splitlines()


def _parse_pytest(pytest_output):
    """Parses 'py.test --collect-only' output."""
    module_str = ''
    for line in pytest_output:
        if '<Module ' in line:
            class_str = instance_str = function_str = ''
            module_str = re.search(r'\'(.*)\'', line).group(1) + '::'

        if 'cfme/tests' not in module_str:
            continue

        if '<Class ' in line:
            instance_str = function_str = ''
            class_str = re.search(r'\'(.*)\'', line).group(1) + '::'
        if '<Instance ' in line:
            function_str = ''
            instance_str = re.search(r'\'(.*)\'', line).group(1) + '::'
        if '<Function ' in line:
            function_str = re.search(r'\'(.*)\'', line).group(1)
            node_id = '{}{}{}'.format(class_str, instance_str, function_str)

            unique_id = node_id.replace('::()', '').replace('::', '.')

            yield unique_id


def _get_pytest_testcases():
    output = _run_pytest()
    all_testcases_gen = _parse_pytest(output)
    return set(all_testcases_gen)


def _get_polarion_testcases(csv_file):
    logger.info('Importing Polarion test cases from {}'.format(csv_file))
    imported_data = get_imported_data(csv_file)
    return {res['title']: res for res in imported_data.results}


def _get_outdated(polarion_testcases, pytest_testcases):
    outdated_titles = set(polarion_testcases) - pytest_testcases
    outdated_db = {}
    for title in outdated_titles:
        outdated_db[title] = polarion_testcases[title]
    return outdated_db


def _write_csv(output_file, outdated_db):
    with open(output_file, 'wb') as csvfile:
        sorted_db = sorted(outdated_db.items(), key=operator.itemgetter(0))
        csv_writer = UnicodeWriter(csvfile)
        csv_writer.writerow([col.title() for col in sorted_db[0][1].keys()])
        for testcase in sorted_db:
            csv_writer.writerow([val for val in testcase[1].values()])
        logger.info('Data written to {}'.format(output_file))


def main(args=None):
    """Main function for cli."""
    logging.basicConfig(format='%(name)s:%(levelname)s:%(message)s', level=logging.INFO)
    args = _get_args(args)

    try:
        polarion_testcases = _get_polarion_testcases(args.input_file)
        pytest_testcases = _get_pytest_testcases()
    # pylint: disable=broad-except
    except Exception as err:
        logger.error('Failed to get data: {}'.format(err))
        return 1

    outdated_db = _get_outdated(polarion_testcases, pytest_testcases)
    if not outdated_db:
        logger.info('No outdated test cases found, not writing {}'.format(args.output_file))
        return 0
    _write_csv(args.output_file, outdated_db)

    return 0


if __name__ == '__main__':
    sys.exit(main())
