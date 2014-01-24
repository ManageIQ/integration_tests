"""
utils.path
----------

Project path helpers

Contains `py.path.local`_ objects for accessing common project locations.

Paths rendered below will be different in your local environment.

.. _py.path.local: http://pylib.readthedocs.org/en/latest/path.html
"""

import os

from py.path import local

_this_file = os.path.abspath(__file__)

#: The project root, ``cfme_tests/``
project_path = local(_this_file).new(basename='..')

#: conf yaml storage, ``cfme_tests/conf/``
conf_path = project_path.join('conf')

#: datafile storage, ``cfme_tests/data/``
data_path = project_path.join('data')

#: log storage, ``cfme_tests/log/``
log_path = project_path.join('log')

#: interactive scripts, ``cfme_tests/scripts/``
scripts_path = project_path.join('scripts')

#: jinja2 templates, use with ``jinja2.FileSystemLoader``
template_path = data_path.join('templates')


def get_rel_path(absolute_path_str):
    """Get a relative path for object in the project root

    Args:
        absolute_path_str: An absolute path to a file anywhere under `project_path`

    Note:

        This will not work for files that are not in `project_path`

    """
    target_path = local(absolute_path_str)
    return target_path.relto(project_path)
