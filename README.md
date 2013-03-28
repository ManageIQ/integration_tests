CloudForms: Management Engine - Tests
=====================================

Setup
-----

1. Copy credentials.yaml, mozwebqa.cfg, pytest.ini from a working cfme_pages project.
1. Create a virtualenv to run pytest from
   - Execute one of the following commands:
     - `pip install virtualenv`
     - `easy_install virtualenv`
     - `yum install python-virtualenv`
   - Create a virtualenv: `virtualenv <name>`
   - To activate the virtualenv later: `source <name>/bin/activate`
1. Set the PYTHONPATH to include cfme_tests *and* cfme_pages. Without this, pages won't be
   importable, and scripts won't work. Edit your virtualenv's `bin/activate` script from the
   previous step. At the end of the file, export a PYTHONPATH variable with paths to the two
   repositories by adding this line (altered to match your repository locations):
   - `export PYTHONPATH='/path/to/cfme_tests:/path/to/cfme_pages'`
1. Ensure the following devel packages are installed (for building python dependencies):
   - gcc
   - postgresql-devel
   - libxml2-devel
   - libxslt-devel
   - `sudo yum install gcc postgresql-devel libxml2-devel libxslt-devel`
1. Install python dependencies:
   - `pip install -Ur /path/to/cfme_tests/requirements.txt`

1. Verify that the tests run.
   - `py.test --driver=firefox --credentials=credentials.yaml --untrusted`

Some of the items in the final step can be put into your environment, and into pytest.ini
so you can then run py.test without arguments. That exercise is left for the reader.

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
