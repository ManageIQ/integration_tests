"""
utils.path
----------

Project path helpers

Contains `py.path.local`_ objects for accessing common project locations.

Paths rendered below will be different in your local environment.

.. _py.path.local: http://pylib.readthedocs.org/en/latest/path.html
"""

import os

import py.path

_this_file = os.path.abspath(__file__)

#: The project root, ``cfme_tests/``
project_path = py.path.local(_this_file).new(basename='..')

#: conf yaml storage, ``cfme_tests/conf/``
conf_path = project_path.join('conf')

#: datafile storage, ``cfme_tests/data/``
data_path = project_path.join('data')

#: log storage, ``cfme_tests/log/``
log_path = project_path.join('log')

#: interactive scripts, ``cfme_tests/scripts/``
scripts_path = project_path.join('scripts')
