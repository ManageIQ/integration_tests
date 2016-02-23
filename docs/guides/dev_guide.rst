Style Guide
===========

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
  functionality that work by themselves and do not result in brokenness of master

  * As an example, if you were working on a test which required new pages,
    utilities and tests, it would be OK to split the page, utility and test
    changes into separate requests or commits, providing they were in the correct
    order of dependency.

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

* When wrapping blocks of long lines, indent the trailing lines once, instead of
  indenting to the opening bracket. This helps when there are large blocks of long
  lines, to preserve some readability::

    _really_really_long_locator_name = (True, 'div > tr > td > a[title="this \
        is just a little too long"]')
    _another_really_super_long_locator_name = (True, 'div > tr > td > \
        a[title="this is getting silly now"]')

- When wrapping long conditionals, indent trailing lines twice, just like with
  function names and any other block statement (they usually end with colons)::

    if this_extremely_long_variable_name_takes_up_the_whole_line and \
            you_need_to_wrap_your_conditional_to_the_next_line:
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

General Notes
"""""""""""""

* Avoid using :py:func:`time.sleep` as much as possible to workaround quirks in the UI.
  There is a :py:func:`utils.wait.wait_for` utility that can be used to wait for
  arbitrary conditions. In most cases there is some DOM visible change on the page
  which can be waited for.
* Avoid using :py:func:`time.sleep` for waiting for changes to happen outside of the UI.
  Consider using tools like mgmt_system to probe the external systems for
  conditions for example and tie it in with a :py:func:`utils.wait.wait_for` as discussed above.
* If you feel icky about something you've written but don't know how to make
  it better, ask someone. It's better to have it fixed before submitting it as
  a pull request ;)

Other useful code style guidelines:

* `PEP 20 - The Zen of Python <http://www.python.org/dev/peps/pep-0020>`_
* `PEP 257 - Docstring Conventions <http://www.python.org/dev/peps/pep-0257>`_

cfme_tests
----------

For page development, please refer to :doc:`page_development`.

Layout
^^^^^^

``cfme_tests/``

* ``cfme/`` Page modeling and tests

  * ``web_ui/`` The new web framework
  * ``fixtures/`` The new fixtures
  * ``tests/`` Tests container

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
* ``metaplugins/`` Plugins loaded by ``@pytest.mark.meta``. Further informations in
  :py:mod:`markers.meta`
* ``utils/`` Utility functions that can be called inside our outside the
  test context. Generally, util functions benefit from having a related test
  fixture that exposes the utility to the tests. Modules in this directory
  will be auto loaded.

  * ``tests/`` Unit tests for utils
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

This Document
-------------

This page is subject to change as our needs and policies evolve. Suggestions
are always welcome.
