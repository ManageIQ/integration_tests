.. _browser_configuration:

Browser Configuration
=====================

All browser configuration is done by editing ``conf/env.yaml``, or creating a local override in
``conf/env.local.yaml``. Local overrides are preferred. For more information about configuration
yamls, see :py:mod:`utils.conf`.

All yaml examples in this document are snippets from ``env.yaml``.


Local vs. Remote
----------------
Most WebDrivers can operate in two modes, as a local WebDriver or through a Remote
WebDriver. The local WebDriver will launch a browser in the calling environment (such as
your desktop), while the Remote WebDriver will connect to a remote selenium server (hence the name)
and attempt to run the browser there.

Examples for each mode will be provided, where appropriate. Note that capitalization is extremely
important when specifying either ``webdriver`` or ``browserName``, as indicated in the examples
below.

Some help for setting up the remote selenium server can be found in the :ref:`vnc_selenium` document.

WebDriver Wharf
---------------

A variant of the Remote webdriver, WebDriver Wharf will spawn docker containers running the selenium
standalone server on request.

Remote desired_capabilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^

All ``Remote`` drivers take a "desired_capabilities" dictionary. Details on what keys and expected
value types can be used in this dictionary can be found in the selenium documentation:

    https://code.google.com/p/selenium/wiki/DesiredCapabilities

Selenium, by default, looks for the selenium server on localhost port 4444. If the selenium server
is running on a different machine, you'll need to add a ``command_executor`` option to
``webdriver_options`` in the examples below to the machine running the selenium server.

``command_exector`` must be a URL to a selenium server hub, which by default is at the ``/wd/hub``
path on the selenium server.

For example::

   browser:
        webdriver: Remote
        webdriver_options:
            command_executor: http://selenium-server-hostname:port/wd/hub
            desired_capabilities:
                browserName: browser

.. note::

    * Each browser has its own set of capabilities, and those capabilities will usually not
      apply from one browser to another.
    * While most selenium identifiers have been translated from ``JavaIdentifiers`` to
      ``python_identifiers``, the keys of ``desired_capabilities`` are not altered in any way.
      No name translation should have to be done for ``desired_capabilities`` keys
      (e.g. ``browserName`` does not become ``browser_name``).


base_url
--------

Regardless of which Webdriver you use, ``base_url`` must be set. It is assumed that the website
at the ``base_url`` will be a working CFME UI.

.. note ::

    ``base_url`` is not solely used by the browser. Other functionality, such as the SSH and SOAP
    clients, derive their destination addresses from the ``base_url``.

Firefox
-------

Firefox has built-in support for selenium (and vice-versa). No additional configuration should be
required to use the Firefox browser.

Local
^^^^^

.. code-block:: yaml

    browser:
        webdriver: Firefox

Remote
^^^^^^

.. code-block:: yaml

    browser:
        webdriver: Remote
        webdriver_options:
            desired_capabilities:
                browserName: firefox

WebDriver Wharf
^^^^^^^^^^^^^^^

.. code-block:: yaml

    browser:
        webdriver: Remote
        webdriver_options:
            desired_capabilities:
                browserName: firefox
        webdriver_wharf: http://wharf.host:4899/

Chrome
------

In order to use Chrome with selenium, you must first install the ``chromedriver`` executable. This
executable should be somewhere on your ``PATH``.

* Download `chromedriver <http://chromedriver.storage.googleapis.com/>`_. Use the latest available
  release for your architecture.
* ``chromedriver`` documentation: https://sites.google.com/a/chromium.org/chromedriver/getting-started

Local
^^^^^

.. code-block:: yaml

    browser:
        webdriver: Chrome

Remote
^^^^^^

.. code-block:: yaml

     browser:
        webdriver: Remote
        webdriver_options:
            desired_capabilities:
                browserName: chrome

WebDriver Wharf
^^^^^^^^^^^^^^^

.. code-block:: yaml

    browser:
        webdriver: Remote
        webdriver_options:
            desired_capabilities:
                browserName: chrome
        webdriver_wharf: http://wharf.host:4899/

Safari
------

Like Firefox, Safari is natively supported by selenium. Usage is equally simple, with the exception
that you'll probably need to be running selenium on OS X.

Local
^^^^^

.. code-block:: yaml

    browser:
        webdriver: Safari

Remote
^^^^^^

.. code-block:: yaml

    browser:
        webdriver: Remote
        webdriver_options:
            # If selenium is running remotely, remember to update command_executor
            #command_executor: http://safari_host/wd/hub
            desired_capabilities:
                browserName: safari

Internet Explorer
-----------------

Like Chrome & ``chromedriver``, Internet Explorer needs a separate executable to work with selenium,
``InternetExplorerDriver``. ``InternetExplorerDriver`` is a server that only runs in Windows, and
should be running before starting selenium in either Local or Remote mode.

* For more information, visit https://code.google.com/p/selenium/wiki/InternetExplorerDriver

Local
^^^^^

.. code-block:: yaml

    browser:
        webdriver: Ie

Remote
^^^^^^

.. code-block:: yaml

    browser:
        webdriver: Remote
        webdriver_options:
            # If selenium is running remotely, remember to update command_executor
            #command_executor: http://windows_host/wd/hub
            desired_capabilities:
                browserName: internet explorer
                # platform must be WINDOWS for IE
                platform: WINDOWS


Sauce Labs
----------

By providing selenium servers on a multitude of platforms, Sauce Labs is able to help us test in
"exotic" environments. In order to test against appliances behind firewalls, sauce-connect must be
used:

    https://saucelabs.com/docs/connect

sauce-connect tunnels are used by default if they're running, so the same ``command_executor`` can
be used to use the sauce labs service whether sauce-connect is running or not::

    command_executor: http://username:apikey@ondemand.saucelabs.com:80/wd/hub

Internet Explorer Sauce
^^^^^^^^^^^^^^^^^^^^^^^

The following example is our "worst-case scenario", which is running a very
recent release of Internet Explorer in a very recent release of Windows:

.. code-block:: yaml

    browser:
        webdriver: Remote
        webdriver_options:
            command_executor: http://username:apikey@ondemand.saucelabs.com:80/wd/hub
            desired_capabilities:
                browserName: internet explorer
                platform: Windows 8.1
                version: 11
                screen-resolution: 1280x1024

The above configuration, at the time of this writing, ran our test suite with no issues.

More information on sauce-specific options allowed in desired_capabilities can be found in
the sauce labs documentation:

    * https://saucelabs.com/platforms
    * https://saucelabs.com/docs/additional-config#desired-capabilities

.. note::

    Python values for the browser constants used in the sauce labs "platform" page can be found here:
    https://code.google.com/p/selenium/source/browse/py/selenium/webdriver/common/desired_capabilities.py

Troubleshooting
---------------

If errors are encountered while launching a selenium browser, check the selenium website to
make sure that your version of selenium matches the latest version. If not, upgrade.

    https://code.google.com/p/selenium/downloads/list
