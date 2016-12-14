Setting up editors
==================

Sublime
-------

The "supported" editor of choice for working on this project is
`Sublime Text 2 <http://www.sublimetext.com>`_ (sublime), though these instructions will likely
also work for Sublime Text 3. Of course you're free to use whichever
editor helps you be the most productive, but the preponderance of Sublime users on the team
make it the most useful target for our development environment setup documentation.

Getting Started
^^^^^^^^^^^^^^^

Get sublime
"""""""""""

To begin, sublime must be installed. It is distributed via a tarball from the
`sublime download page <http://www.sublimetext.com/2>`_. This tarball can be extracted anywhere.
A likely place is in your home folder. Once extracted, run the ``sublime_text`` executable in the
new directory to start the editor.

Configure sublime for Python
""""""""""""""""""""""""""""

By default, sublime will attempt to autodetect indentation. When this autodetection fails,
it will fall back to using 4-space tab stops, but using tabs instead of spaces. To easily
address this, open any .py in the editor, and then select ``Preferences > Settings - More >
Syntax Specific - User`` from the menu. This should open up ``Python.sublime-settings``.
In this file, enter the following options and save:

.. code-block:: json

  {
      "detect_indentation": false,
      "rulers": [100],
      "tab_size": 4,
      "translate_tabs_to_spaces": true,
      "use_tab_stops": true
  }

This will force python files to match our code style guidelines, which use spaces instead of
tabs with an indentation of 4 spaces.

The ``rulers`` option will also draw a vertical line at 100 characters as a visual aid to keep
lines from getting too long. Additional integer values can be added to the ``rulers`` list; it
might be useful to also have a rule at 80 columns as a "soft limit", for example.

Package Control
"""""""""""""""

Once sublime is up and running, we'll need to install some package management, which we'll be
using hereafter to bring in sublime extensions. Follow the installation instructions
`here <https://sublime.wbond.net/installation#st2>`_. Be sure to follow the instructions for
Sublime Text 2, unless you're beta testing Sublime Text 3.

.. note:: When installing packages, it is sometimes necessary to restart sublime for the
   installed packages to initialize. For simplicity, it is probably easiest to restart sublime
   after installing any package. Restarting sublime after changing configuration files should
   not be necessary.

SublimeCodeIntel
""""""""""""""""

Install the SublimeCodeIntel package. Select ``Preferences > Package Control`` from the program
menu, then choose "Install Package". Enter "SublimeCodeIntel". Once installed, SublimeCodeIntel
will provide autocompletion for imports and function/method calls.

SublimeCodeIntel will autodetect python names from project directories (visible in the sidebar)
for autocompletion, but it won't detect builtins or installed libraries. To enable this,
SublimeCodeIntel needs to be given a hint. It looks for config files in ``.codeintel`` directories
inside of project directories, so we'll be putting the hint there. The ``cfme_tests`` directory
is the perfect place for the ``.codeintel`` directory,  so ensure that the ``cfme_tests`` directory
has been added to your current project. If not, ``Project > Add Folder to Project...``, and select
your ``cfme_tests`` directory.

Using your tool of choice (for example, a shell or sublime itself), make the ``.codeintel`` directory
under ``cfme_tests``. Inside that directory, create and edit the file
``config`` (``cfme_tests/.codeintel/config``). Like most sublime configuration files, the content of
this file is a python dictionary. It looks very similar to JSON, which is used in most
sublime configuration files, so be mindful of the different syntax.

Insert the following::

  {
      "Python":
      {
          "codeintel_scan_files_in_project": True,
          "python": "/path/to/virtualenv/bin/python",
          "pythonExtraPaths":
          [
              "/path/to/virtualenv/lib/python2.7/site-packages"
          ]
      }
  }

Remember to change the ``/path/to/virtualenv`` strings to be the actual path to your virtualenv.
``python`` should point to the virtualenv's python interpreter.

Relative paths can be used here, and will be relative to the project folder (in this case,
``cfme_tests``), not the location of this config file. So, if ``cfme_tests`` is in the same
directory as the virtualenv's ``bin`` and ``lib`` directory, The paths for ``python`` and
``pythonExtraPaths`` could start with ``../bin`` and ``../lib``, respectively.

Flake8 Lint
"""""""""""

Using Package Control, install the "Python Flake8 Lint" package. To apply our specific style
exceptions to this package, edit the configuration. Via the menu, choose ``Preferences >
Package Settings > Python Flake8 Lint > Settings - User``. In the settings file that opens,
enter our exceptions:

.. code-block:: json

  {
        "pep8_max_line_length": 100,
        "ignore": ["E128"]
  }

Flake8 lint will pop up every time you save a file, and does an excellent job of keeping you
linted while you code.

Trailing Spaces
"""""""""""""""

Using Package Control, install the "Trailing Spaces" plugin. This highlights trailing spaces
so you can clean them up before flake8 sees them.

Sublime Text 3
--------------

Sublime Text 3 is currently in beta, but it is perfectly usable for python development. I will show
you my setup here (``mfalesni``). Prerequisities are the same as for ST2 (Package Control).

Recommended Extensions and Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SublimePythonIDE
""""""""""""""""
It is a rewrite of SublimeRope for ST3. It is both Python Autocompletion and PEP8 checker.
Install it from package manager the same way is described in chapter about ST2.

After installation, go to ``Preferences -> Package Settings -> SublimePythonIDE -> User`` and insert
this code:

.. code-block:: json

   {
      "open_pydoc_in_view": true,
      "create_view_in_same_group": false,

      "python_linting": true,
      "python_linter_mark_style": "outline",
      "python_linter_gutter_marks": true,
      "python_linter_gutter_marks_theme": "alpha",
      "pep8": true,
      "pep8_ignore": ["E128"],
      "pep8_max_line_length": 100,
      "pyflakes_ignore": []
   }

For the project file (``Project -> Edit Project``), use this code:

.. code-block:: json

   {
     "folders":
     [
       {
         "follow_symlinks": true,
         "path": "/home/mfalesni/sublime-workspace/cfme_tests",
       },

       {
         "follow_symlinks": true,
         "path": "/home/mfalesni/sublime-workspace/whatever_else_directory_you_need",
       },
     ],

     "settings":
     {
       "python_interpreter": "/home/mfalesni/sublime-workspace/.cfme_tests_ve/bin/python",
       "tab_size": 4,
     },
   }


Of course, replace the paths according to your setup. ``python_interpreter`` is the path for your
virtualenv python.

From now, Sublime will know about all modules that are in virtualenv/cfme_tests namespace.

When you right-click a symbol, you can view a documentation, or jump to the symbol definition.

GitGutter
"""""""""
Very good plugin, showing you lines that are added/modified/removed in your git repository in form
of marks on left side of the editor window. (first suggested by jkrocil)

BracketHighlighter
""""""""""""""""""
Simple plugin that shows you location of brackets, parenthesis and others that you are in on left
side of editor window.

Neon color scheme
"""""""""""""""""
You might find default colour theme a bit humdrum. I use Neon color scheme, which uses more colours
and the colouring depends on the context so one has better view on the situation.

To install, simply install ``Neon Color Scheme`` package. Then open ``Preferences -> Settings - User``
and add this entry ``"color_scheme": "Packages/Neon Color Scheme/Neon.tmTheme"`` to the conf dict.

Python Improved
"""""""""""""""""
Together with Neon, this package makes python source code better readable. Install with package
manager ``C-P -> Install Package -> Python Improved``. Then after installation, open whatever
python source file you like, click ``View -> Syntax -> Open all with current extension as ...`` and
select PythonImproved.


emacs
-----

So far the best emacs setup I've (``jweiss``) found is iPython notebook, combined with the `ein
<http://tkf.github.io/emacs-ipython-notebook/>`_ emacs package (emacs iPython notebook).

Installing iPython and its Emacs client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

iPython 
"""""""

See the install `docs <http://ipython.org/install.html>`_.

ein
"""

`Emacs iPython Notebook <http://tkf.github.io/emacs-ipython-notebook/>`_ is the emacs client for
iPython.

The official ein package does not work with the latest ipython. I built a package from the `fork
<https://github.com/millejoh/emacs-ipython-notebook>`_ of ein that does work.  You can get the
package from the internal repository listed below.  You should also add the `Melpa
<http://melpa.milkbox.net/#/>`_ repository.


.. code-block:: cl

 (add-to-list 'package-archives
   '("melpa" . "http://melpa.milkbox.net/packages/") t)
 (add-to-list 'package-archives
   '("jweiss" . "http://qeblade5.rhq.lab.eng.bos/isos/emacs-package-archive/") t)

You can then run ``M-x package-install``, ``ein`` in emacs to install ein.

Then in a shell somewhere, you can start up iPython notebook process.  This is the python process
that will intepret all the code you will be sending it.

.. code-block:: bash

   $ source ~/my-virtual-env/bin/activate
   $ cd ~/my-project
   $ ipython notebook

Then in emacs, run ``M-x ein:notebooklist-open``.  It will prompt you for a port (default 8888).
This will bring up the EIN environment, where you can evaluate python snippets (and edit them and
evaluate them again).  You can also save the notebook to use your snippets again later.  The outputs
are also saved.

Starting iPython from within Emacs
""""""""""""""""""""""""""""""""""

I wrote a little bit of elisp to start a iPython notebook process for you from within emacs.  It's
easier than having to type shell commands every time.  It requires the ``magit`` package, which I
highly recommend (it is a git client for emacs).

.. code-block:: cl

   (autoload 'magit-get-top-dir "magit" nil t)

   (defun magit-project-dir ()
     (magit-get-top-dir (file-name-directory (or (buffer-file-name) default-directory))))

   (defun start-ipython-current-project (virtualenv-dir)
     (interactive
      (let ((d (read-directory-name "VirtualEnv dir: " "~/.virtualenvs/" nil t)))
        (list d)))
     (save-excursion
       (let ((buf (get-buffer-create
                   (generate-new-buffer-name (file-name-nondirectory
                                              (directory-file-name (file-name-directory (magit-project-dir))))))))
         (shell buf)
         (process-send-string buf (format ". %s/bin/activate\n" virtualenv-dir))
         (process-send-string buf (format "cd %s;ipython notebook\n" (magit-project-dir))))))


To use the above snippet,

* Go to any buffer that's visiting any file in your project (or any buffer whose ``pwd`` is in your project)
* ``M-x start-ipython-current-project``
* At the prompt, input the directory where your virtualenv lives

It will start ipython in emacs' shell buffer.

Autosave Notebooks
""""""""""""""""""

Unlike the iPython web interface, ein does not autosave notebooks by default.  Here is a snippet
that will enable autosave (notebooks are saved every time you execute a cell)

.. code-block:: cl

  ;; ein save worksheet after running cell
  (eval-after-load 'ein-multilang
    '(defadvice ein:cell-execute (after ein:save-worksheet-after-execute activate)
       (ein:notebook-save-notebook-command)))


Flake8 Lint
^^^^^^^^^^^

Flycheck is recommended because it highlights the column where the problem occurs instead of just the line.

Run ``M-x package-install``, ``flycheck``, and see the `Flycheck homepage <https://github.com/flycheck/flycheck>`_.

You can use the global mode as described on the homepage, or to just enable flymake for python files

.. code-block:: cl

  (autoload 'flycheck "flycheck-mode")
  (eval-after-load 'python
    '(add-hook 'python-mode-hook 'flycheck-mode))

Recommended
^^^^^^^^^^^

:Magit:

   Emacs client for git and a huge time saver.  All git commands are a single keypress, pretty views
   of diffs, branches, remotes, etc.  Package is ``magit``.

:Ido and Smex:

   ``ido`` package (now built into emacs) for filename and buffer name completion, ``smex`` for
   ``M-x`` command completion.

:Smartparens: 

   Inserts parens, brackets, quotes, etc in pairs.  Keeps parens balanced, allows you to edit
   paren-delimited structures logically instead of as plain text (designed for lisp but also works
   on html, xml, json, etc).  Replaces paredit, an older and more well-known tool that does the same
   thing.  Package ``smartparens``.

:Autocomplete: 

   Code completion for emacs.  Package is called ``autocomplete``, see ``ein`` docs for how to enable in
   python buffers.

:Undo Tree:

   Edit with confidence! Keeps track of all your buffer changes, even stuff you undid and re-did on
   top of.  Package is called ``undo-tree``.

:yagist:
   
   Create a github gist (paste) from a region or buffer with a single keypress, and the link to the
   gist is automatically inserted into the clipboard so you can easily paste it into IRC.

:Multiple cursors:

   Extremely powerful editing tool, best described with `this
   video. <http://emacsrocks.com/e13.html>`_ Package is ``multiple-cursors``.
