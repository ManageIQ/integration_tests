Contributors Guide
==================

General Guidelines
------------------

Contributing
^^^^^^^^^^^^

* Own your pull requests; **you** are their advocate.

  * If a request goes unreviewed for two or three days, ping a reviewer to see
    what's holding things up.
  * Follow up on open pull requests and respond to any comments or questions a
    reviewer might have.

* Keep the contents of the pull request focused on one idea. Smaller pull
  requests are easier to review, and thus will be merged in more quickly.
* After submitting a request, be ready to work closely with a reviewer to get it
  tested and integrated into the overall test suite.
* Follow the `Code Style`_ guidelines to make your pull request as easy to review
  as possible.
* If your request requires the use of private information that can't be
  represented in the data file templates (probably cfme_data.yaml), please
  state that in the test module docstring or the individual test docstring,
  along with information on where that data can be found.
* Similar to the last point, any data files used by a test module should be
  clearly documented in that module's docstring.
* Any data required in a sensitive data file should be reflected in the
  template for that file.
* Standards may change over time, so copying older code with similar
  functionality may not be the most productive action. If in doubt, refer back
  to this document and update the copied code according to the current
  guidelines.
* Please keep large lint changes separate from new features, though this point
  should become less relevant over time.
* All pull requests should be squashed down to logical blocks of distinctive
  functionality that work by themselves and do not result in brokenness of master.

  * As an example, if you were working on a test which required new pages,
    utilities and tests, it would be OK to split the page, utility and test
    changes into separate requests or commits, providing they were in the correct
    order of dependency.

* It is a good practice to sign your commits.

  * You will need to generate a GPG key with gpg version 2.1.17 or greater and
    sign your commits. See [this link](https://help.github.com/articles/generating-a-new-gpg-key/)
    for information about how to do that. Some instalations on Linux may
    require you to use ``gpg2`` instead of ``gpg``.
  * Remember to sign your commit by using ``-S|--gpg-sign``.
  * There are some checks being made when your pull request is opened. They
    are used to verify the signature in your commits. If you are external
    to the ManageIQ team, those checks will fail because we do not have
    access to your generated keys, but you can safely ignore them.

Reviewers
^^^^^^^^^

Reviewers will be looking to make sure that the `Contributing`_ guidelines are
being met. Some of the things that go into the review process:

* Assign the PR to the reviewer
* Pull request branches will be rebased against current master before testing.
* Newly added tests will be run against a clean appliance.
* Adherence to code style guidelines will be checked.

If tests fail, reviewers *WILL*:

* ...give you a complete traceback of the error.
* ...give you useful information about the appliance against which tests were run,
  such as the appliance version.
* ...give you insight into any related data files used.

If tests fail, reviewers *WILL NOT*:

* ...thoroughly debug the failing test(s).

All requests require 2 approvals from two reviewers, after which time, the contributor
may, permissions allowing, merge the commit him/herself.

**Reviewers must never approve their own pull requests.**

Release Candidates and Tagging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The MIQ/integration_tests maintainers will use a two week release schedule, with a release candidate
(RC) commit tagged on the last Friday in the cycle.  When this RC tag is set, new PRs are not
accepted for merging unless fixing things that were broken in the current release cycle.
This 2-3 day period is commonly called the 'dev-freeze'.

Release tags will be created on the following Tuesday, and the downstream-stable branch updated
to the release tag commit.

Releases are tagged with a version number in the format ``\d+\.\d+\.\d+``,
for example ``17.25.0``.

The release candidate commits will be tagged on Friday with a ``downstream-stable-rc`` tag,
and a version numbered tag that will match the version number of the *next* release.
For example, the Friday before ``17.25.0`` is released we create an RC tag ``17.25.0-rc``.

This means we have a tag, ``downstream-stable-rc`` that moves each time an RC commit is selected,
and a 2nd tag pointing to the same commit with a ``-rc`` suffix.

This process breaks down to something like the following. This example is for release ``18.30.0``

#. On Friday, reviewers feverishly merge any PRs that have passed review and have good PRT results.
#. Once all merge-able PRs have been considered, a ``master`` branch commit is selected for RC.
#. For this example, the commit is ``abcde1234``
#. A Maintainer creates ``18.30.0-rc`` tag, and force updates ``downstream-stable-rc`` tag
#. Both tags point to ``abcde1234``
#. We are now in dev-freeze, and no PRs will be merged until release (exception below)
#. RC test jobs start, using the ``downstream-stable-rc`` tag as their git ref.
#. Everyone has a great weekend and the RC jobs run a full test run against all providers
#. Monday/Tuesday, test results are analyzed
#. PRs are opened against any new failures, labeled with ``rc-regression-fix``
#. ``rc-regression-fix`` PRs are reviewed, tested, and merged  (exception for dev-freeze)
#. Tuesday, a ``master`` branch commit is selected for release, ``abcde1235``
#. The ``18.30.0`` tag is created
#. The ``downstream-stable`` branch is updated (fast-forward)
#. Both ``downstream-stable`` branch and ``18.30.0`` point to commit ``abcde1235``
#. Release email sent with changelist of the included PRs
#. 'dev-freeze' is over, and PRs can now be merged at-will into ``master``


Code Style
^^^^^^^^^^

We adhere to Python's `PEP 8 style guide <http://www.python.org/dev/peps/pep-0008/>`_
, occasionally allowing exceptions for the sake of readability. This is covered in the
`Foolish Consistency <http://www.python.org/dev/peps/pep-0008/#a-foolish-consistency-is-
the-hobgoblin-of-little-minds>`_ section of PEP 8. Information on using linting tools to
help with this can be found on the :doc:`lint` page.

We also do a few things that aren't explicitly called out in PEP 8:

* The github pull request pane is our primary code review medium, and has a minimum
  width of 100 characters. As a result, our maximum line length is 100 characters,
  rather than 80.

* Use parentheses ``()`` for line continuation::

    # in imports
    import (module1, module2, module3, module4,
        module5)

        or

    import (
        module1, module2, module3,
        module4)

        or

    import (
        module1,
        module2,
        module3
    )

    # in long strings without multiple lines
    very_long_string = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt "
        "ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
        "ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur "
        "sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id "
        "est laborum."
    )

* Docstrings can be used in strings with multiple lines::

    string_with_multiple_lines = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
    nostrud exercitation"""


* When wrapping blocks of long lines, indent the trailing lines once, instead of
  indenting to the opening bracket. This helps when there are large blocks of long
  lines, to preserve some readability::

    _really_really_long_locator_name = (True, ('div > tr > td > a[title="this '
        'is just a little too long"]'))
    _another_really_super_long_locator_name = (True, ('div > tr > td > '
        'a[title="this is getting silly now"]'))

- When wrapping long conditionals, indent trailing lines twice, just like with
  function names and any other block statement (they usually end with colons)::

    if (this_extremely_long_variable_name_takes_up_the_whole_line and
            you_need_to_wrap_your_conditional_to_the_next_line):
        # Two indents help clearly separate the wrapped conditional
        # from the following code.

- When indenting a wrapping sequence, one indent will do. Don't try to align
  all of the sequence items at an arbitrary column::

    a_good_list = [
        'item1',
        'item2',
        'item3'
    ]

    a_less_good_list = [ 'item1',
                         'item2',
                         'item3'
    ]

* According to PEP 8, triple-quoted docstrings use double quotes. To help
  differentiate docstrings from normal multi-line strings, consider using
  single-quotes in the latter case::

    """This is a docstring.

    It follows PEP 8's docstring guidelines.

    """

    paragraph = '''This is a triple-quoted string, with newlines captured.
    PEP 8 and PEP 257 guidelines don't apply to this. Using single quotes here
    makes it simple for a reviewer to know that docstring style doesn't apply
    to this text block.'''

* On the subject of docstrings (as well as comments) +++use them+++. Python is
  somewhat self-documenting, so use docstrings and comments as a way to
  explain not just what code is doing, but why it's doing what it is, and what
  it's intended to achieve.

  We have decided to use the following docstring format and use the `Cartouche
  <https://github.com/rob-smallshire/cartouche>`_
  Sphinx plugin to generate nice docs. Details on the format can be found above,
  but an example is described below::

    def my_function(self, locator):
        """Runs the super cool function on a locator

        Seriously, you have to try this

        Note: You don't actually have to try it

        Args:
            locator: The name of a locator that can be described by using
                multiple lines.

        Returns:
            Nothing at all.

        Raises:
          CertainQuestionsError: Raises certain questions about the authors sanity.
        """

* Use `TODO` comment for workaround, temporary or not perfect code.
  A `TODO` comment begins with the string `TODO` all in caps. It can be use with some identifier
  like Name or Email (i.e. the person responsible for improvement), Bugzilla, Github Issue etc.
  An example is described below::

    # TODO: <todo message>
    # TODO(ndhandre): <todo message>
    # TODO(ndhandre@redhat.com): <todo message>
    # TODO(BZ-1687061): <todo message>

* In addition to being broken up into the three sections of standard library,
  third-party, and the local application, imports should be sorted
  alphabetically. 'import' lines within those sections still come before
  'from ... import' lines::

    import sys
    from os import environ
    from random import choice

* We require ``print`` statements be written in Python 3.0 compatible format, that is
  encased in parentheses::

    print("Hello")

* We also use the newer ``.format`` style for string formatting and will no longer be accepting
  the older ``%s`` format. The new format offers many more enhancements::

    a = "new"
    b = 2

    "a {} string for {}".format(a, b)

    "{name} is {emotion}".format(name="john", emotion="happy")

    "{0} and another {0}".format("something")

* There is a one exception for string formatting. According
  `<https://docs.python.org/3/howto/logging.html#optimization>`_ use old style ``%s``,
  but without the actual ``%`` formatting operation::

    from cfme.utils.log import logger

    logger.info("Some message %s", some_string)

General Notes
"""""""""""""

* Avoid using :py:func:`time.sleep` as much as possible to workaround quirks in the UI.
  There is a :py:func:`cfme.utils.wait.wait_for` utility that can be used to wait for
  arbitrary conditions. In most cases there is some DOM visible change on the page
  which can be waited for.
* Avoid using :py:func:`time.sleep` for waiting for changes to happen outside of the UI.
  Consider using tools like mgmt_system to probe the external systems for
  conditions for example and tie it in with a :py:func:`cfme.utils.wait.wait_for` as discussed above.
* If you feel icky about something you've written but don't know how to make
  it better, ask someone. It's better to have it fixed before submitting it as
  a pull request ;)

Other useful code style guidelines:

* `PEP 20 - The Zen of Python <http://www.python.org/dev/peps/pep-0020>`_
* `PEP 257 - Docstring Conventions <http://www.python.org/dev/peps/pep-0257>`_

UI modeling
-----------

For a guide on how to model the UI representation in our framework, please see :doc:`ui_modeling`.

Layout
^^^^^^

``cfme_tests/``

* ``cfme/`` Page modeling and tests

  * ``fixtures/`` The new fixtures
  * ``tests/`` Tests container
  * ``utils/`` Utility functions that can be called inside our outside the
    test context. Generally, util functions benefit from having a related test
    fixture that exposes the utility to the tests. Modules in this directory
    will be auto loaded.

    * ``tests/`` Unit tests for utils

* ``conf/`` Place for configuration files
* ``data/`` Test data. The structure of this directory should match the
  structure under ``cfme/tests/``, with data files for tests in the same relative
  location as the test itself.

  * For example, data files for ``cfme/tests/dashboard/test_widgets.py`` could go into
    ``data/dashboard/test_widgets/``.

* ``fixtures/`` py.test fixtures that can be used by any test. Modules in
  this directory will be auto loaded.
* ``markers/`` py.test markers that can be used by any test. Modules in this
  directory will be auto loaded.
* ``cfme/metaplugins/`` Plugins loaded by ``@pytest.mark.meta``. Further informations in
  :py:mod:`markers.meta`

* ``scripts/`` Useful scripts for QE developers that aren't used during
  a test run
* ``sprout/`` Here lives the Sprout appliance tool.

Writing Tests
^^^^^^^^^^^^^

Tests in `cfme_tests` have the following properties:

* They pass on a freshly deployed appliance with no configuration beyond the
  defaults (i.e. tests do their own setup and teardown).
* Where possible, they strive to be idempotent to facilitate repeated testing
  and debugging of failing tests. (Repeatable is Reportable)
* Where possible, they try to clean up behind themselves. This not only helps
  with idempotency, but testing all of the
  `CRUD <http://en.wikipedia.org/wiki/CRUD>`_ interactions helps to make a
  thorough test.
* Tests should be thoroughly distrustful of the appliance, and measure an
  action's success in as many ways as possible. A practical example:

  * Do not trust flash messages, as they sometimes tell lies (or at least
    appear to). If you can go beyond a flash message to verify a test
    action, do so.

Some points when writing tests:

* When naming a test, do not use a common part of multiple test names as a test
  name itself. In the example below, trying to run a single test called
  ``test_provider_add``, not only runs that test, but also ``test_provider_add_new``
  and ``test_provider_add_delete``, as pytest uses string matching for test names.
  ``test_provider_add`` should have a suffix making it unique. In this way a tester
  can choose the run just the single test on its own, or the group of tests, whose
  names all begin the same way.

  * test_provider_add - Adds a provider (**Bad naming**)
  * test_provider_add_new - Adds a new provider type
  * test_provider_add_delete - Adds a provider and then deletes it

* Where a clean-up is required, it should be carried out in a Finalizer. In this
  way we prevent leaving an appliance dirty if the test fails as the clean up will
  happen regardless.
* Keep all properties, fixtures and functions together

Fixtures
^^^^^^^^

Fixtures are not only responsible for setting up tests, but also cleaning up
after a test run, whether that test run succeeded or failed.
`addfinalizer <http://pytest.org/latest/funcargs.html#_
pytest.python.FuncargRequest.addfinalizer>`_ is very powerful. finalizer functions
are called even if tests fail.

When writing fixtures, consider how useful they might be for the overall
project, and place them accordingly. Putting fixtures into a test module
is rarely the best solution. Instead, try to put them in the nearest
conftest.py. If they're generic/useful enough consider putting them into
one of the `fixtures/` directory for use in `cfme_tests` or the `plugin/`
directory for use in both projects.

Requirements workflow
^^^^^^^^^^^^^^^^^^^^^
We have recently updated our requirements workflow in the hope that it provides a more
streamlined experience. The requirements workflow revolves around the ``miq requirement``
command:

.. code-block:: console

    Usage: miq requirement [OPTIONS] COMMAND [ARGS]...

      Functions for adding, updating, and freezing requirements

    Options:
      --help  Show this message and exit.

    Commands:
      add          Add and install/update a package to current virtualenv.
      freeze       Freeze all requirements (non-imported and imported)
      remove       Remove and uninstall a package from the current virtualenv.
      scan         Scan repository files for imports from pip-installable...
      upgrade      Upgrade (or downgrade) a package to version specified, or...
      upgrade-all  Scan and update all packages that are not constrained


To understand the impacts of each of these commands we must first discuss the requirements
files that we have included. They are:

1. ``requirements/template_scanned.txt``:
    This template file contains the package names
    (no versions) that have been detected in import statements in the repo. This file
    is updated automatically through the ``miq requirement scan`` command. Contributors can
    also add directly to this file via the ``miq requirement add <package-name>`` command.
2. ``requirements/template_non_imported.txt``:
    This template file contains package names (no versions) of packages that are not directly
    imported, but are needed for tooling/development.
    Things like pre-commit, cfme-testcases, pytest-polarion-collect. This can be updated manually
    or through the ``miq requirement add -e`` the additional option ``e`` is what makes it considered
    an extra/additional package.
3. ``requirements/constraints.txt``:
    This file specifies any version constraints we must impose on any of the packages in
    ``template_scanned.txt`` and ``template_non_imported.txt``. It also includes any version
    constraints we must impose on any dependencies of those packages. This file can be
    edited manually or by specifying a version when you use the ``add`` command e.g.
    ``miq requirement add <package-name>==0.1``
4. ``requirements/frozen.txt``:
    This file should never be edited manually. Instead if you upgrade or add a package, you
    should run ``miq requirement freeze`` to update this. This file is used by our automation and
    quickstart.

Help text for each of the commands:

1. ``miq requirement add``

.. code-block:: console

    Usage: miq requirement add [OPTIONS] PACKAGE_NAME

      Add and install/update a package to current virtualenv.

    Options:
      --scan-template TEXT    The path to the template file (pip -r arg) for
                              scanned imports, will be overwritten  [default:
                              requirements/template_scanned_imports.txt]
      --extra-template TEXT   The path to the template file (pip -r arg) for extra
                              packages (e.g. pre-commit), will be overwritten
                              [default: requirements/template_non_imported.txt]
      --constraint-file TEXT  The path to the constraint file (pip -r arg) for
                              extra packages (e.g. pre-commit), will be
                              overwritten  [default: requirements/constraints.txt]
      -e, --extra             Is the package an extra package, i.e. not imported
                              [default: False]
      --upgrade               Upgrade an existing package to the most recent
                              version.  [default: False]
      --help                  Show this message and exit.

2. ``miq requirement freeze``

.. code-block:: console

    Usage: miq requirement freeze [OPTIONS]

      Freeze all requirements (non-imported and imported)

    Options:
      --frozen-file TEXT  The path to the frozen file for ALL imports  [default:
                          requirements/frozen.txt]
      --help              Show this message and exit.

3. ``miq requirement scan``

.. code-block:: console

    Usage: miq requirement scan [OPTIONS]

      Scan repository files for imports from pip-installable packages

    Options:
      --scan-template TEXT    The path to the template file (pip -r arg) for
                              scanned imports, will be overwritten  [default:
                              requirements/template_scanned_imports.txt]
      --constraint-file TEXT  The path to the constraint file (pip -r arg) for
                              extra packages (e.g. pre-commit), will be
                              overwritten  [default: requirements/constraints.txt]
      --package-map TEXT      The path to the package map for tricky imports
                              [default: requirements/package_map.yaml]
      --help                  Show this message and exit.


4. ``miq requirement upgrade-all``

.. code-block:: console

    Usage: miq requirement upgrade-all [OPTIONS]

      Scan and update all packages that are not constrained

    Options:
      --scan-template TEXT   The path to the template file (pip -r arg) for
                             scanned imports, will be overwritten  [default:
                             requirements/template_scanned_imports.txt]
      --extra-template TEXT  The path to the template file (pip -r arg) for extra
                             packages (e.g. pre-commit), will be overwritten
                             [default: requirements/template_non_imported.txt]
      --frozen-file TEXT     The path to the frozen file for ALL imports
                             [default: requirements/frozen.txt]
      -f, --freeze           Freeze requirements after updating.  [default: False]
      --help                 Show this message and exit.

5. ``miq requirement upgrade``

.. code-block:: console

    Usage: miq requirement upgrade [OPTIONS] PACKAGE_NAME

    Upgrade (or downgrade) a package to version specified, or latest version

    Options:
    --constraint-file TEXT  The path to the constraint file (pip -r arg) for
                          extra packages (e.g. pre-commit), will be
                          overwritten  [default: requirements/constraints.txt]
    --extra-template TEXT   The path to the template file (pip -r arg) for extra
                          packages (e.g. pre-commit), will be overwritten
                          [default: requirements/template_non_imported.txt]
    --scan-template TEXT    The path to the template file (pip -r arg) for
                          scanned imports, will be overwritten  [default:
                          requirements/template_scanned_imports.txt]
    -e, --extra             Is the package an extra package, i.e. not imported
                          [default: False]
    --help                  Show this message and exit.
This command is really an alias to the ``miq requirement add`` command. It has the added
benefit of that if you run ``miq requirement upgrade <package-name>`` on a package that
currently has constraints defined, it will install the most recent version and remove the
constraint from ``requirements/constraints.txt``. IMPORTANT NOTE: you still must pass
the ``-e, --extra`` parameter if the package is an non-imported package.

6. ``miq requirement remove``

.. code-block:: console

    Usage: miq requirement remove [OPTIONS] PACKAGE_NAME

      Remove and uninstall a package from the current virtualenv.

    Options:
      --scan-template TEXT    The path to the template file (pip -r arg) for
                              scanned imports, will be overwritten  [default:
                              requirements/template_scanned_imports.txt]
      --extra-template TEXT   The path to the template file (pip -r arg) for extra
                              packages (e.g. pre-commit), will be overwritten
                              [default: requirements/template_non_imported.txt]
      --constraint-file TEXT  The path to the constraint file (pip -r arg) for
                              extra packages (e.g. pre-commit), will be
                              overwritten  [default: requirements/constraints.txt]
      --help                  Show this message and exit.

This command will uninstall the package and remove it from ``template_non_import.txt``,
``template_scanned.txt``, and ``constraints.txt``, if it is in those files.

Bugzilla Guide
^^^^^^^^^^^^^^
See the :doc:`./bugzilla`

This Document
-------------

This page is subject to change as our needs and policies evolve. Suggestions
are always welcome.
