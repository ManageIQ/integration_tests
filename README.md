CloudForms: Management Engine - Tests
=====================================

Setup
-----

1. Create a virtualenv from which to run tests
   - Execute one of the following commands:
     - `pip install virtualenv`
     - `easy_install virtualenv`
     - `yum install python-virtualenv`
   - Create a virtualenv: `virtualenv <name>`
   - To activate the virtualenv later: `source <name>/bin/activate`
1. [Fork and Clone](https://help.github.com/articles/fork-a-repo) this repository into
   the new virtualenv
1. Set the PYTHONPATH to include cfme_tests. Edit your virtualenv's `bin/activate` script,
   created with the virtualenv. At the end of the file, export a PYTHONPATH variable with the
   path to the repository clone by adding this line (altered to match your repository locations):
   - `export PYTHONPATH='/path/to/virtualenv/cfme_tests'`
1. Ensure the following devel packages are installed (for building python dependencies):
   - gcc
   - postgresql-devel
   - libxml2-devel
   - libxslt-devel
   - *yum* users: `sudo yum install gcc postgresql-devel libxml2-devel libxslt-devel`
1. Install python dependencies:
   - `pip install -Ur /path/to/virtualenv/cfme_tests/requirements.txt`
1. Copy template files in cfme_tests to the same file name without the .template extension
   - Example: `cp file.name.template file.name`
   - Bash script example: `for file in *.template; do cp -n $file ${file/.template}; done`
1. Edit the copied files as needed to reflect your environment.
1. Verify that the tests run (in the cfme_tests dir in the virtualenv)
   - `py.test --driver=firefox --credentials=credentials.yaml --untrusted`

Some of the items in the final step can be put into your environment, and into pytest.ini
so you can then run py.test without arguments. That exercise is left for the reader.

Activitive the virtualenv
-------------------------

The virtualenv is activated on creation. To reactivate the virtualenv in subsequent sessions,
the `bin/activate` script must be sourced.
- Bash example:
  - `cd /path/to/virtualenv'
  - `source bin/activate` or `. bin/activate`

Contributing
--------------

Submit a pull request from a fork to contribute.

With regard to design, if a component can be shared between different pages (trees, accordions,
etc.), then it should be turned into a region. This is a standalone bit of code that models just a
small portion of a page. From there, these regions can be composited into a page object. Page
objects themselves should expose properties that represent items on the page, and also any
"services" that the page has. So, rather than write a test with 'Fill in username, fill in password
click submit', you would create a 'login' method on the page that takes the username and password
as an argument. This will shield the tests from changing implementation of that login method. If
you want pass something different, create a new method, like 'login_with_enter_key', so as to allow
other variations of the service.

If an action results in navigation to a new page, and that page will always be known, the action
should return the page that results.

The elements and methods exposed on a page will result from tests written against that page. If
there is a specific test that you are working on, write the test first, modeling the page as you go
(if needed) to provide the necessary functionality. Developers are not expected or encourage to
model pages without a test that uses the modeling.

The Mozilla style guide below has great examples and guidance on writing tests against page models,
as well as the page models themselves.

All contributions will be checked for compliance with the
[Developer Guidelines](https://github.com/RedHatQE/cfme_tests/wiki/Developer-Guidelines). Users are
expected to [lint](https://github.com/RedHatQE/cfme_tests/wiki/linty-freshness) their code before
submitting a pull request. Pull requests are an excellent collaborative review medium; feel free to
open up pull requests before code is "ready" to get feedback and suggestions from other developers.

Background
--------------

The testing framework being used is py.test:
http://pytest.org/latest

We are also using a plugin from the mozwebqa people to integrate py.test with Selenium:
https://github.com/davehunt/pytest-mozwebqa

Mozilla style guide, contains some useful guidelines for making good page objects:
https://wiki.mozilla.org/QA/Execution/Web_Testing/Docs/Automation/StyleGuide

Using Chrome
------------

1. Download from http://code.google.com/p/chromedriver/downloads/list.
   Use the latest available for your architecture.
1. Extract the `chromedriver` exectuable from that archive into your virtualenv's `bin`
   directory (alongside `bin/activate`)
1. Substitue the py.test `--driver=firefox` parameter with `--driver=chrome`

More Information
----------------

Head over to the [project wiki](https://github.com/RedHatQE/cfme_tests/wiki) for more
information, including developer guidelines and some tips for working with selenium.
