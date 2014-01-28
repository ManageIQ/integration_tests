Documenting cfme_tests
======================

Overview
--------

In addition to `PEP 257`_, inline documentation of the cfme_tests code adheres to the
`Google Python Style Guide`_. The Google-recommended docstring format is very easy to both
read and write, and thanks to the `cartouche`_ library, it's parseable by `sphinx`_, which
we use to generate our documentation.

The documentation is built and hosted by the excellent `readthedocs`_ service, but
should be `built locally <#building-the-docs>`_ before making a pull request.

docstrings
----------

The cartouche library parses our docstrings and turns them into nicely rendered API docs
in the sphinx output. As such, we should follow cartouche's usage guidelines when writing
docstrings:

    http://cartouche.readthedocs.org/en/latest/usage.html

According to PEP 257, docstrings should use triple double-quotes, not triple single-quotes
(""" vs. ''').

Example:

.. code:: python

    """This is a docstring."""

    '''This is not a docstring.'''

Linking new modules
-------------------

As new modules are created, they'll need to be added to the documentation tree. This starts in the
``toctree`` directive in ``docs/index.rst``. Each entry in that tree references other .rst files
in the docs/ directory, which can in turn reference documentation sources in their own ``toctree``
directives (ad infinitum).

Once the rst file has been inserted into the ``toctree`` (assuming one had to be created), sphinx
needs to be told to generate documentation from the new code. We use sphinx's autodoc feature
to do this, and it looks like this::

    .. automodule:: packagename.modulename

The paramater passed to the ``automodule`` should be the importable name of the module to be
documented, ``cfme.login`` for example.

There is no hard and fast rule for where things should go in the toctree, but do try to keep the
docs well-organized.

Building the Docs
-----------------

Prior to pushing up new code, preview any new documentation by building to docs locally.
You can do this using the sphinx-build command. From the ``cfme_tests`` directory::

    sphinx-build -b html docs/ docs/build/

This will build html documentation based on the sources in the docs/ directory, and put them
in the docs/build/ directory, which can then be opened in a browser::

    google-chrome docs/build/index.html
    # or...
    firefox docs/build/index.html

Old and busted
--------------

The "legacy" code (contained mainly in the ``pages/`` and ``tests/`` directories) will not be
documented here. Time spent documenting that code is better spent converting it to the new page
style, in the ``cfme/`` directory.

.. link refs
.. _`pep 257`: http://www.python.org/dev/peps/pep-0257/
.. _`google python style guide`: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html#Comments
.. _`cartouche`: http://cartouche.readthedocs.org/
.. _`sphinx`: http://sphinx-doc.org/
.. _`readthedocs`: https://readthedocs.org/
