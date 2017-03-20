Getting Started
===============


Before you start 
-----------------
Welcome to the Getting Started Guide. The CFME QE team is glad that you have decided to read this
page that will help you understand how ``cfme_tests`` interacts with the appliances. There are some
important information contained within this text, so we would like you to spend some time to
carefully read this page from beginning to the end. That will make you familiarize with the process
and will minimize the chance of doing it wrong. Then you can proceed the shortest way using the
setup and execution scripts.


Obtaining what you need (Project Setup)
----------------------------------------

* create a dedicated folder for working with the integration tests,
  our automated quickstart has expectations that best work out
  when it has its own place
* obtain the ``cfme_tests`` repository
  (`fork and clone <https://github.com/ManageIQ/integration_tests/fork>`_)
* if you have access, obtain the ``cfme-qe-yamls`` repository (internal url, please ask the team) and
  put the ``.yaml_key`` file into the root of the ``cfme_tests`` repository.
* enter the ``cfme_tests`` repository with your shell and execute ``python -m cfme.scripting.quickstart``
  which will in turn configure your system, the development environment and the default configuration files
* activate the development environment by ``. ../cfme_venv/bin/activate``
* Set up a local selenium server that opens browser windows somewhere other than your
  desktop. There is a Docker based solution for the browser, look at the script
  ``scripts/dockerbot/sel_container.py``. That ensures you have the proper versions of browsers. You
  can also set everything up in your system using Xvnc - :doc:`guides/vnc_selenium` .

Appliances in containers
------------------------
If the target appliance you will be testing is a container, you might like to consult
:doc:`guides/container` for the details specific to testing containers.


Running Tests
==============

* Test! Run miq-runtest. (This takes a long time, Ctrl-C will stop it)
* When miq-runtest ends or you Ctrl-C it, it will look stuck in the phase "collecting artifacts". You
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
    parameters. If you run your code outside of ``miq-runtest`` run, you MUST use ``utils.ports``
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
  to the ``miq-runtest`` command. Due to a glitch that has not been resolved yet, you should set the
  ``base_url`` to the first appliance.

* If you have access to Sprout, you can request a fresh appliance to run your tests, you can use
  command like this one:

  .. code-block:: bash

     SPROUT_USER=username SPROUT_PASSWORD=verysecret miq-runtest <your pytest params> --use-sprout --sprout-group "<stream name>" --sprout-appliances N

  If you specify ``N`` greater than 1, the parallelized run is set up automatically. More help
  about the sprout parameters are in :py:mod:`fixtures.parallelizer`. If you don't know what
  the sprout group is, check the dropdown ``Select stream`` in Sprout itself.



Browser Support
---------------

We support any browser that selenium supports, but tend to run Firefox or Chrome.

For detailed instructions on setting up different browsers, see :ref:`browser_configuration`.
