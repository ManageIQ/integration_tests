Getting Started
===============

Setup
-----

* Create a virtualenv from which to run tests

  * Execute one of the following commands:

    * ``pip install virtualenv``
    * ``easy_install virtualenv``
    * ``yum install python-virtualenv``

  * Create a virtualenv: ``virtualenv <name>``
  * To activate the virtualenv later: ``source <name>/bin/activate``

* Fork and Clone this repository into the new virtualenv
* Set the ``PYTHONPATH`` to include ``cfme_tests``. Edit your virtualenv's ``bin/activate`` script,
  created with the virtualenv. At the end of the file, export a PYTHONPATH variable with the path to
  the repository clone by adding this line (altered to match your repository locations):

  * ``export PYTHONPATH='/path/to/virtualenv/cfme_tests'``

* Also add this line at the end of your virtualenv to prevent .pyc files polluting your folders:

  * ``export PYTHONDONTWRITEBYTECODE="yes"``

* Make sure you set the shared secret for the credentials files encryption. There are two ways:

  * add ``export CFME_TESTS_KEY="our shared key"`` into the activate script
  * create ``.yaml_key`` file in project root containing the key


* Ensure the following devel packages are installed (for building python dependencies):

  * ``gcc``
  * ``postgresql-devel``
  * ``libxml2-devel``
  * ``libxslt-devel``
  * ``zeromq3-devel``
  * ``libcurl-devel``
  * yum users: ``sudo yum install gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel``

* Install python dependencies:

  * ``PYCURL_SSL_LIBRARY=nss pip install -Ur /path/to/virtualenv/cfme_tests/requirements.txt``
  * If you forget to use the ``PYCURL_SSL_LIBRARY`` env variable and you get a pycurl error, you
    have to run it like this to fix it:

    * Ensure you have ``libcurl-devel`` installed (this was not a prerequisite before so it can
      happen)
    * Run ``PYCURL_SSL_LIBRARY=nss pip install -U -r requirements.txt --no-cache-dir``

* Copy template files in cfme_tests to the same file name without the ``.template`` extension

  * Example: ``cp file.name.template file.name``
  * Bash script example: ``for file in *.template; do cp -n $file ${file/.template}; done``
  * Edit these files as needed to reflect your environment.

* Do the same for the config yamls in the conf directory, using Configuration YAMLs

  * Example: ``cd conf/; cp env.local.template env.local``
  * Then edit ``conf/env.local.yaml`` to override ``base_url``

* Set up a local selenium server that opens browser windows somewhere other than your
  desktop by running :doc:`guides/vnc_selenium`
* Test! Run py.test. (This takes a long time, Ctrl-C will stop it)

.. note::
   In the past, the pytest_mozwebqa package was used to help manage the web browser and
   selenium session. We've recently done away with it, so you can safely
   ``pip uninstall pytest_mozwebqa``. pytest_mozwebqa provided many commandline options
   (for example: ``--driver``, ``--baseurl``, ``--credentials``, ``--untrusted``). These
   will all need to be removed from the py.test invocation (or addopts line in pytest.ini)
   if mozwebqa is uninstalled.

Activating the virtualenv
-------------------------

The virtualenv is activated on creation. To reactivate the virtualenv in subsequent sessions,
the ``bin/activate`` script must be sourced.

.. code-block:: bash

   #Bash example:
   `cd /path/to/virtualenv'
   source bin/activate or . bin/activate

Testing Framework
-----------------

The testing framework being used is `py.test <http://pytest.org/latest>`_

Browser Support
---------------

We support any browser that selenium supports, but tend to run Firefox or Chrome.

For detailed instructions on setting up different browsers, see :ref:`browser_configuration`.
