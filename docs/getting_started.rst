Getting Started
===============

Setup
-----
You can use this shortcut to install the system and python dependencies which will leave you only
with the need to copy the yamls and putting the ``.yaml_key`` in place. Copy this to an executable
file, place it in the ``cfme_tests`` repository (along ``conftest.py``):

.. code-block:: bash

  #!/usr/bin/env bash

  if hash dnf;
  then
    YUM=dnf
  else
    YUM=yum
  fi

  sudo $YUM install -y python-virtualenv gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel redhat-rpm-config
  virtualenv .cfme_tests
  echo "export PYTHONPATH='`pwd`'" | tee -a ./.cfme_tests/bin/activate
  echo "export PYTHONDONTWRITEBYTECODE=yes" | tee -a ./.cfme_tests/bin/activate

  . ./.cfme_tests/bin/activate
  PYCURL_SSL_LIBRARY=nss pip install -Ur ./requirements.txt
  echo "Run '. ./.cfme_tests/bin/activate' to load the virtualenv"

Detailed steps (manual environment setup):

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

* Get the shared encryption key for credentials. Ask in CFME QE.
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
  * ``redhat-rpm-config`` if you use some kind of really stripped system.
  * Fedora (possibly RHEL-like systems) users:
    * ``hash dnf 2>/dev/null && { YUM=dnf; } || { YUM=yum; }``
    * ``sudo $YUM install gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel redhat-rpm-config``

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

Using the testing framework (for newbies or non-CFMEQE core people)
--------------------------------------------------------------
Our team relies on a lot of internal tools that simplify life to the QEs. If eg. a developer would
like to run ``cfme_tests`` on his/her system, here are some tools and tips that should get you
started as quickly as possible:

* ``cfme_tests`` expects an appliance, with an IP visible to machine with ``cfme_tests`` running
  
  * If this is not the case (eg. CFME behind NAT, a container, whatever), you have to specify the
    ``base_url`` in configuration with a port, which is quite obvious, but people tend to forget
    ``cfme_tests`` also uses SSH and Postgres extensively, therefore you need to have those services
    accessible and ideally on the expected ports. If you don't have them running on the expected
    ports, you have to specify them manually using ``--port-ssh`` and ``--port-db`` command-line
    parameters.

* ``cfme_tests`` also expects that the appliance it is running against is configured. By
  'configured', we mean the database is set up and seeded (therefore UI running), database
  permissions loosened so ``cfme_tests`` can access it and a couple of other fixes. Check out
  :py:meth:`utils.appliance.IPAppliance.configure`, and subsequent method calls.
  
  * Framework contains code that can be used to configure the appliance exactly as ``cfme_tests``
    desires. There are two ways of using it:

    * Instantiate :py:class:`utils.appliance.Appliance` or :py:class:`utils.appliance.IPAppliance`,
      depending on whether you want to use IP or provider name with VM name. Then simply run the
      :py:meth:`utils.appliance.Appliance.configure` or :py:meth:`utils.appliance.IPAppliance.configure`
      depending on which class you use. Then just wait and watch logs.

    * You can run exactly the same code from shell. Simply run:

      .. code-block:: bash

         scripts/ipappliance.py configure ipaddr1 ipaddr2 ipaddr3...

      Which enables you to configure multiple appliances in parallel.

* Using :py:class:`utils.appliance.Appliance` only makes sense for appliances on providers that
  are specified in ``cfme_data.yaml``.

* Previous bullet mentioned the ``scripts/ipappliance.py`` script. This script can call any method
  or read any property located in the :py:class:`utils.appliance.IPAppliance`. Check the script's
  header for more info. The call to that method is threaded per-appliance, so it saves time.
  Despite the parallelization, the stdout (one line per appliance - return value of the method)
  prints in the same order as the appliances were specified on the command line, so it is suitable
  for further shell processing if needed.

* Similarly, you can use  ``scripts/appliance.py`` script for interacting with the
  :py:class:`utils.appliance.Appliance` methods. It is a bit older and has slightly different usage.
  And lacks threading.

* If you want to test a single appliance, set the ``base_url`` in the ``conf/env.yaml``

* If you want to test against multiple appliances, use the ``--appliance w.x.y.z`` parameter. Eg. if
  you have appliances ``1.2.3.4`` and ``2.3.4.5``, then append ``--appliance 1.2.3.4 --appliance 2.3.4.5``
  to the ``py.test`` command. Due to a glitch that has not been resolved yet, you should set the
  ``base_url`` to the first appliance.

* If you have access to Sprout, you can request a fresh appliance to run your tests, you can use
  command like this one:

  .. code-block:: bash

     SPROUT_USER=username SPROUT_PASSWORD=verysecret py.test <your pytest params> --use-sprout --sprout-group "<stream name>" --sprout-appliances N

  If you specify ``N`` greater than 1, the parallelized run is set up automatically. More help
  about the sprout parameters are in :py:mod:`fixtures.parallelizer`. If you don't know what
  the sprout group is, check the dropdown ``Select stream`` in Sprout itself.



Browser Support
---------------

We support any browser that selenium supports, but tend to run Firefox or Chrome.

For detailed instructions on setting up different browsers, see :ref:`browser_configuration`.
