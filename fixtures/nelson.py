import os
from textwrap import dedent
from types import FunctionType

from six import iteritems
from sphinxcontrib.napoleon import _skip_member, Config
from sphinxcontrib.napoleon import docstring
from sphinxcontrib.napoleon.docstring import NumpyDocstring
import sphinx

from utils.log import get_rel_path, logger

config = Config(napoleon_use_param=True, napoleon_use_rtype=True)


def pytest_pycollect_makeitem(collector, name, obj):
    """pytest hook that adds docstring metadata (if found) to a test's meta mark"""
    if not isinstance(obj, FunctionType) and not hasattr(obj, 'meta'):
        # This relies on the meta mark having already been applied to
        # all test functions before this hook is called
        return

    # __doc__ can be empty or nonexistent, make sure it's an empty string in that case
    doc = getattr(obj, '__doc__') or ''
    p = GoogleDocstring(stripper(doc), config)

    obj.meta.kwargs.update({
        'from_docs': p.metadata
    })
    if p.metadata:
        test_path = get_rel_path(collector.fspath)
        logger.debug('Parsed docstring metadata on {} in {}'.format(name, test_path))
        logger.trace('{} doc metadata: {}'.format(name, str(p.metadata)))


def stripper(docstring):
    """Slightly smarter :func:`dedent <python:textwrap.dedent>`

    It strips a docstring's first line indentation and dedents the rest

    """
    lines = docstring.splitlines()
    return os.linesep.join([
        lines[0].strip(), dedent("\n".join(lines[1:]))
    ])


class GoogleDocstring(docstring.GoogleDocstring):
    """Custom version of napoleon's GoogleDocstring that adds some special cases"""
    def __init__(self, *args, **kwargs):
        self.metadata = {}
        super(GoogleDocstring, self).__init__(*args, **kwargs)
        self._sections['usage'] = self._parse_usage_section
        self._sections['metadata'] = self._parse_metadata_section
        super(GoogleDocstring, self)._parse()

    def _parse(self):
        pass

    def _consume_usage_section(self):
        lines = self._dedent(self._consume_to_next_section())
        return lines

    def _consume_metadata_section(self):
        lines = self._dedent(self._consume_to_next_section())
        return lines

    def _parse_usage_section(self, section):
        b = ['.. rubric:: Usage:', '']
        c = ['.. code-block:: python', '']
        lines = self._consume_usage_section()
        lines = self._indent(lines, 3)
        return b + c + lines + ['']

    def _parse_metadata_section(self, section):
        lines = self._consume_metadata_section()
        for line in lines:
            if line:
                key, value = [kv.strip() for kv in line.split(':')]
                self.metadata[key] = value
        return ['']


def setup(app):
    """Sphinx extension setup function.

    See Also:
        http://sphinx-doc.org/extensions.html

    """
    from sphinx.application import Sphinx
    if not isinstance(app, Sphinx):
        return  # probably called by tests

    app.connect('autodoc-process-docstring', _process_docstring)
    app.connect('autodoc-skip-member', _skip_member)

    for name, (default, rebuild) in iteritems(Config._config_values):
        app.add_config_value(name, default, rebuild)
    return {'version': sphinx.__version__, 'parallel_read_safe': True}


def _process_docstring(app, what, name, obj, options, lines):
    result_lines = lines
    if app.config.napoleon_numpy_docstring:
        docstring = NumpyDocstring(result_lines, app.config, app, what, name,
                                   obj, options)
        result_lines = docstring.lines()
    if app.config.napoleon_google_docstring:
        docstring = GoogleDocstring(result_lines, app.config, app, what, name,
                                    obj, options)
        result_lines = docstring.lines()
    lines[:] = result_lines[:]
