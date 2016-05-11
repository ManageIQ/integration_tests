Getting Started
===============

Before you start copypasting ...
--------------------------------
Welcome to the Getting Started Guide. The CFME QE team is glad that you have decided to read this
page that will help you understand how ``cfme_tests`` interacts with the appliances. There are some
important information contained within this text, so we would like you to spend some time to
carefully read this page from beginning to the end. That will make you familiarize with the process
and will minimize the chance of doing it wrong. Then you can proceed the shortest way using the
setup and execution scripts.


opinionated quick.start script
--------------------------------

The opinionated quick-start script builds expects a certain base setup
and leaves you with a usable enabled virtualenv.

* you are in a checkout of ``cfme_tests``
* you have a checkout of the RedHat internal repository
  with the encrypted credentials
* you already put ``.yaml_key`` in place
* you are fine with symlinks instead of copies of the yaml data
* you run RHEL/Fedora or installed the build requirements on your own
* you use bash as shell

::
  $ . ./scripts/quickstart.sh
  ...
  (.cfme_tests)$


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

  sudo $YUM install -y python-virtualenv gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel redhat-rpm-config gcc-c++ openssl-devel libffi-devel
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
  * To activate the virtualenv later: ``source <name>/bin/activate``, but do not do it yet, it still
    needs finishing touches.

* Fork and Clone this repository.
* Set the ``PYTHONPATH`` to include ``cfme_tests``. Edit your virtualenv's ``bin/activate`` script,
  created with the virtualenv. At the end of the file, export a PYTHONPATH variable with the path to
  the repository clone by adding this line (altered to match your repository locations):

  * ``export PYTHONPATH='/path/to/cfme_tests_repo'``

* Also add this line at the end of your virtualenv to prevent .pyc files polluting your folders:

  * ``export PYTHONDONTWRITEBYTECODE="yes"``

* If you forgot to do that and you have ``pyc`` files polluting your folders, this is a cure, placed
  in ``~/.bashrc`` and usable everywhere:

  .. code-block:: bash

    alias rmpyc='find . -name \*.pyc -delete; find . -name __pycache__ -delete'

  Reload your ``.bashrc`` and issue ``rmpyc`` command.

* Get the shared encryption key (``.yaml_key``) for credentials. Ask in CFME QE.
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
  * ``gcc-c++``
  * ``openssl-devel``
  * ``libffi-devel``
  * Fedora (possibly RHEL-like systems) users:

    * ``hash dnf 2>/dev/null && { YUM=dnf; } || { YUM=yum; }``

    * ``sudo $YUM install gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel redhat-rpm-config gcc-c++ openssl-devel libffi-devel``

    * On RHEL and derived systems, it will say the zeromq package is not available but that is ok.

* Activate the virtual environment:

To activate the virtualenv, the ``bin/activate`` script must be sourced. Bear in mind that you
should have the two options added in the ``bin/activate`` script BEFORE you source it, otherwise it
will not work.

.. code-block:: bash

   #Bash example:
   `cd /path/to/virtualenv'
   source bin/activate or . bin/activate

* Install python dependencies:

  * ``PYCURL_SSL_LIBRARY=nss pip install -Ur /path/to/virtualenv/cfme_tests/requirements.txt``
  * If you get error from pycurl and you used this command, you might like to remove pycurl and try
    installing it again with different SSL library set. The error message should give you an idea
    what to try. For reinstallation, you will need to use the command mentioned in next bullet.
  * If you forget to use the ``PYCURL_SSL_LIBRARY`` env variable and you get a pycurl error, you
    have to run it like this to fix it:

    * Ensure you have ``libcurl-devel`` installed (this was not a prerequisite before so it can
      happen)
    * Run ``PYCURL_SSL_LIBRARY=nss pip install -U -r requirements.txt --no-cache-dir``

* You copy/symlink the required YAML files into ``conf/`` if you have access to team's internal YAML
  repository. Required YAML files are ``env``, ``cfme_data``, ``credentials``. If the file's
  extension is ``.yaml`` it is loaded normally, if its extension is ``.eyaml`` then it is encrypted
  and you need to have the decryption key in the ``cfme_tests/`` directory. You can also start them
  from scratch by copying the templates in ``conf/`` and editing them to suit the environment you
  use.
* Set up a local selenium server that opens browser windows somewhere other than your
  desktop. There is a Docker based solution for the browser, look at the script
  ``scripts/dockerbot/sel_container.py``. That ensures you have the proper versions of browsers. You
  can also set everything up in your system using Xvnc - :doc:`guides/vnc_selenium` .
* Test! Run py.test. (This takes a long time, Ctrl-C will stop it)
* When py.test ends or you Ctrl-C it, it will look stuck in the phase "collecting artifacts". You
  can either wait about 30 seconds, or you can Ctrl-C it again.
* In either case, check your processes sometimes, the artifactor process likes to hang when forced
  to quit, but it can also happen when it ends normally, though it is not too common.

Testing Framework
-----------------

The testing framework being used is `py.test <http://pytest.org/latest>`_

Execution script
-----------------
An execution script (cfme_test.sh) is provided. This script handles orchestration of
docker, virtualenv, and cfme_test.

Configure path to your virtualenv and your ``cfme_test`` repository in the ``cfme_tests/conf/env.local.yaml``.

.. code-block:: yaml

  tmux:
      PYTHON_ENV_PATH: 'path/to/virtualenv/bin'
      CFME_TEST_PATH: 'path/to/cfme_tests_repo'

The script requires shyaml (`pip install shyaml`) and tmux (`yum install tmux`) commands.

.. code-block:: bash

   #Bash example:
   cd /path/to/cfme_test
   ./cfme_test.sh

Navigating within the console:

* Command mode: ctrl+shift+b

  - up/down to change pane

  - '[' to scroll within a pane

    + press the 'Esc' key to exit scrolling




More tmux commands can be found here: https://tmuxcheatsheet.com/

Using the testing framework (for newbies or non-CFMEQE core people)
-------------------------------------------------------------------
Our team relies on a lot of internal tools that simplify life to the QEs. If eg. a developer would
like to run ``cfme_tests`` on his/her system, here are some tools and tips that should get you
started as quickly as possible:

* ``cfme_tests`` expects an appliance, with an IP visible to the machine that runs ``cfme_tests``

  * If this is not the case (eg. CFME behind NAT, a container, whatever), you MUST specify the
    ``base_url`` in configuration with a port, which is quite obvious, but people tend to forget
    ``cfme_tests`` also uses SSH and Postgres extensively, therefore you MUST have those services
    accessible and ideally on the expected ports. If you don't have them running on the expected
    ports, you MUST specify them manually using ``--port-ssh`` and ``--port-db`` command-line
    parameters. If you run your code outside of ``py.test`` run, you MUST use ``utils.ports``
    to override the ports (that is what the command-line parameters do anyway). The approach using
    ``utils.ports`` will be most likely discontinued in the future in favour of merging that
    functionality inside :py:class:`utils.appliance.IPAppliance` class. Everything in the repository
    touching this functionality will get converted with the merging of the functionality when that
    happens.

* ``cfme_tests`` also expects that the appliance it is running against is configured. Without it it
  won't work at all! By configured, we mean the database is set up and seeded (therefore UI
  running), database permissions loosened so ``cfme_tests`` can access it and a couple of other
  fixes. Check out :py:meth:`utils.appliance.IPAppliance.configure`, and subsequent method calls.
  The most common error is that a person tries to execute ``cfme_tests`` code against an appliance
  that does not have the DB permissions loosened. The second place is SSH unavailable, meaning that
  the appliance is NAT-ed

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

    * Unfortunately, these scripts do not work with non-default ports as of now, so you have to do
      the steps manually if setting up such appliance.

* Previous bullet mentioned the ``scripts/ipappliance.py`` script. This script can call any method
  or read any property located in the :py:class:`utils.appliance.IPAppliance`. Check the script's
  header for more info. The call to that method is threaded per-appliance, so it saves time.
  Despite the parallelization, the stdout (one line per appliance - return value of the method)
  prints in the same order as the appliances were specified on the command line, so it is suitable
  for further shell processing if needed.

* Similarly, you can use  ``scripts/appliance.py`` script for interacting with the
  :py:class:`utils.appliance.Appliance` methods. It is a bit older and has slightly different usage.
  And lacks threading.

* Using :py:class:`utils.appliance.Appliance` only makes sense for appliances on providers that
  are specified in ``cfme_data.yaml``.

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
