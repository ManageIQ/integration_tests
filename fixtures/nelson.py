import os
import re
import base64
from textwrap import dedent
from types import FunctionType

from six import iteritems
from sphinx.ext.napoleon import _skip_member, Config
from sphinx.ext.napoleon import docstring
from sphinx.ext.napoleon.docstring import NumpyDocstring
import sphinx
import yaml

from utils.log import get_rel_path, logger

config = Config(napoleon_use_param=True, napoleon_use_rtype=True)


def get_meta(obj):
    doc = getattr(obj, '__doc__') or ''
    p = GoogleDocstring(stripper(doc), config)
    return p.metadata


def pytest_collection_modifyitems(items):
    output = {}
    for item in items:
        item_class = item.location[0]
        item_class = item_class[:item_class.rfind('.')].replace('/', '.')
        item_name = item.location[2]
        item_param = re.findall('\.*(\[.*\])', item_name)
        if item_param:
            item_name = item_name.replace(item_param[0], '')
        node_name = '{}.{}'.format(item_class, item_name)
        output[node_name] = {}
        output[node_name]['docstring'] = base64.b64encode(getattr(item.function, '__doc__') or '')
        output[node_name]['name'] = item_name

        # This is necessary to convert AttrDict in metadata, or even metadict(previously)
        # into serializable data as builtin doesn't contain instancemethod and gives us issues.
        doc_meta = {k: v for k, v in item._metadata.get('from_docs', {}).items()}
        output[node_name]['metadata'] = {'from_docs': doc_meta}

    with open('doc_data.yaml', 'w') as f:
        def dice_representer(dumper, data):
            return dumper.represent_scalar("chew", "me")
        import lya
        from yaml.representer import SafeRepresenter
        yaml.add_representer(lya.lya.AttrDict, SafeRepresenter.represent_dict)
        yaml.dump(output, f)


def pytest_pycollect_makeitem(collector, name, obj):
    """pytest hook that adds docstring metadata (if found) to a test's meta mark"""
    if not isinstance(obj, FunctionType) and not hasattr(obj, 'meta'):
        # This relies on the meta mark having already been applied to
        # all test functions before this hook is called
        return

    # __doc__ can be empty or nonexistent, make sure it's an empty string in that case
    metadata = get_meta(obj)

    if not hasattr(obj.meta, 'kwargs'):
        obj.meta.kwargs = dict()
    obj.meta.kwargs.update({
        'from_docs': metadata
    })
    if metadata:
        test_path = get_rel_path(collector.fspath)
        logger.debug('Parsed docstring metadata on {} in {}'.format(name, test_path))
        logger.trace('{} doc metadata: {}'.format(name, str(metadata)))


def stripper(docstring):
    """Slightly smarter :func:`dedent <python:textwrap.dedent>`

    It strips a docstring's first line indentation and dedents the rest

    """
    if docstring:
        lines = docstring.splitlines()
        return os.linesep.join([
            lines[0].strip(), dedent("\n".join(lines[1:]))
        ])
    else:  # If docstring is a null string, GoogleDocstring will expect an iterable type
        return ''


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
        if lines:
            self.metadata = yaml.load("\n".join(lines))
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
