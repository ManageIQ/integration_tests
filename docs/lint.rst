flake8
======

There are many handy tools that can be used to check your code against established python style. A
tool called `flake8` exists to combine these tools into one easy-to-use package. `flake8` is used
by reviewers on pull requests for style compliance, so it's a good idea to run `flake8` before
submitting code for review.

.. note:: All new content in pull requests is expected to pass flake8 linting.

Manual Invocation
-----------------

To use flake8 in our project, first install it: ``pip install flake8`` or ``easy_install flake8``.

Some flags are required to deal with our specific alterations to python style:

* We allow lines up to 100 characters in length; add ``--max-line-length=100``
* We indent block statement line continuations twice, even in function defs; add ``--ignore=E128``

Then, aim it at the python file (or files) being edited::

   flake8 --max-line-length=100 --ignore=E128 path/to/python_module.py
   flake8 --max-line-length=100 --ignore=E128 path/to/python/package/`

These settings can be stored as defaults in a config file. By default, flake8 looks in
``~/.config/flake8``. Here is an example file that adheres to our style guidelines:

.. code-block:: ini

  [flake8]
  ignore = E128
  max-line-length = 100


IDE Integration
---------------

Sublime Text 2 & 3
^^^^^^^^^^^^^^^^^^

The excellent `Flake8 Lint <https://sublime.wbond.net/packages/Python%20Flake8%20Lint>`_ for the
sublime text editor will do automatic linting using the flake8 tool.
To configure it to follow our guidelines, Add the following options to your
``Flake8Lint.sublime-settings`` file:

.. code-block:: yaml

   "pep8_max_line_length": 100
   "ignore": ["E128"]


Emacs
^^^^^

See `flymake-python-pyflakes.el <https://github.com/purcell/flymake-python-pyflakes>`_.

If you have Melpa or Marmalade package repos already set up, you can install the package by
``M-x package-install``, ``flymake-python-pyflakes``.

To activate on all Python files, add this to your emacs configuration:

.. code-block:: cl

   (autoload 'flymake-python-pyflakes-load "flymake-python-pyflakes" nil t)
   (eval-after-load 'python
     '(add-hook 'python-mode-hook 'flymake-python-pyflakes-load))

To use flake8 and our particular rules:

* ``M-x customize-group``, ``flymake-python-pyflakes``
* Set ``Flymake Python Pyflakes Executable`` to ``flake8``
* Add to ``Flymake Python Pyflakes Extra Arguments``:
  * ``--max-line-length=100``
  * ``--ignore=E128``

Others
^^^^^^

If your IDE isn't listed here, feel free to add instructions above!
