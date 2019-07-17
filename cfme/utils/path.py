"""Project path helpers

Contains `py.path.local`_ objects for accessing common project locations.

Paths rendered below will be different in your local environment.

.. _py.path.local: http://pylib.readthedocs.org/en/latest/path.html
"""
import imp

from py.path import local

_cfme_package_dir = local(imp.find_module('cfme')[1])

#: The project root, ``cfme_tests/``
project_path = _cfme_package_dir.dirpath()


#: conf yaml storage, ``cfme_tests/conf/``
conf_path = project_path.join('conf')

#: datafile storage, ``cfme_tests/data/``
data_path = project_path.join('data')

#: doc root, where these file came from! ``cfme_tests/docs/``
docs_path = project_path.join('docs')

#: log storage, ``cfme_tests/log/``
log_path = project_path.join('log')

#: results path for performance tests, ``cfme_tests/results/``
results_path = project_path.join('results')

#: patch files (diffs)
patches_path = data_path.join('patches')

#: interactive scripts, ``cfme_tests/scripts/``
scripts_path = project_path.join('scripts')

#: interactive scripts' data, ``cfme_tests/scripts/data``
scripts_data_path = scripts_path.join('data')

#: jinja2 templates, use with ``jinja2.FileSystemLoader``
template_path = data_path.join('templates')

#: orchestration datafile storage, ``cfme_tests/data/orchestration``
orchestration_path = data_path.join('orchestration')

#: resource files root directory, ``cfme_tests/data/resources``
resources_path = data_path.join('resources')

#: requirements files directory, `` cfme_tests/requirements``
requirements_path = project_path.join('requirements')


def get_rel_path(absolute_path_str):
    """Get a relative path for object in the project root

    Args:
        absolute_path_str: An absolute path to a file anywhere under `project_path`

    Note:

        This will be a no-op for files that are not in `project_path`

    """
    target_path = local(absolute_path_str)
    # relto returns empty string when no path parts are relative
    return target_path.relto(project_path) or absolute_path_str
