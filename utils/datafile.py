"""datafile functions, to help reliably datafiles from the data directory."""
from __future__ import unicode_literals
import os
from string import Template
from tempfile import NamedTemporaryFile

from jinja2 import Environment, FileSystemLoader

from utils.path import template_path


def load_data_file(filename, replacements=None):
    """Opens the given filename, returning a file object

    Args:
        filename: If a base_path string is passed, filename will be loaded from there
        replacements: If a replacements mapping is passed, the loaded file is assumed to
            be a `template <http://docs.python.org/2/library/string.html#template-strings>`_.
            In this case the replacements mapping will be used in that template's subsitute method.
    Returns: A file object.
    """
    if replacements is None:
        return open(filename)
    else:
        with open(filename) as template_file:
            template = Template(template_file.read())

        output = template.substitute(replacements)

        outfile = NamedTemporaryFile()
        outfile.write(output)
        outfile.flush()
        outfile.seek(0)
        return outfile


def data_path_for_filename(filename, base_path, testmod_path=None):
    """ Returns the data path for a given file name"""
    if testmod_path:
        # remove the base path from testmod path
        test_path_fragment = testmod_path[len(base_path):]

        # remove the .py extension
        test_path_fragment = test_path_fragment.rsplit('.py', 1)[0]

        # remove the tests dir (really just the first occurance of 'tests')
        test_path_fragment = test_path_fragment.replace('tests', '', 1)

        # clean up any extraneous slashes or spaces
        test_path_fragment = test_path_fragment.strip('/ ').replace('//', '/')

        # put it all back together, getting the absolute fs path to filename
        # in the data dir related to testmod_path
        new_path = os.path.join(base_path, 'data', test_path_fragment, filename)
    else:
        # No testmod_path? Well that's a lot easier!
        # Just join it with the data root, minus its leading slash
        new_path = os.path.join(base_path, 'data', filename)

    return new_path


template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)
