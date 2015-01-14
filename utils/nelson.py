from six import iteritems
from sphinxcontrib.napoleon import _skip_member, Config
from sphinxcontrib.napoleon import docstring
from sphinxcontrib.napoleon.docstring import NumpyDocstring
import sphinx


def stripper(docstring):
    lines = docstring.split("\n")

    indent = 100
    for line in lines[1:]:
        whitespace = line.lstrip()
        if whitespace:
            indent = min(indent, len(line) - len(whitespace))

    trimmed_lines = [lines[0].strip()]
    for line in lines[1:]:
        trimmed_line = line[indent:].rstrip()
        trimmed_lines.append(trimmed_line)

    return "\n".join(trimmed_lines)


class GoogleDocstring(docstring.GoogleDocstring):
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

    When the extension is loaded, Sphinx imports this module and executes
    the ``setup()`` function, which in turn notifies Sphinx of everything
    the extension offers.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        Application object representing the Sphinx process

    See Also
    --------
    The Sphinx documentation on `Extensions`_, the `Extension Tutorial`_, and
    the `Extension API`_.

    .. _Extensions: http://sphinx-doc.org/extensions.html
    .. _Extension Tutorial: http://sphinx-doc.org/ext/tutorial.html
    .. _Extension API: http://sphinx-doc.org/ext/appapi.html

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
