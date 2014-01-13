Selenium over VNC
=================

Purpose
-------

The goal of this page is to explain how to set up a remote display that can run selenium tests, and manage/contain test-related web browser windows.

.. note:: This document assumes that you're running a recent Fedora release, and already have a working selenium setup for cfme_pages as explained in the cfme_pages README.

While these instructions are specific to tigervnc, available in Fedora 11 onward, they can be easily adapted to use other VNC packages.

Install requirements
--------------------

We'll need a VNC server (tigervnc-server), a lightweight window manager to run inside that VNC server (fluxbox), and a terminal emulator that can run inside the lightweight window manager (xterm)::

    # yum install tigervnc-server fluxbox xterm

We'll also need the standalone selenium server, which will run inside the VNC server. You'll have to download the Selenium Server jar from their download page (the file should start with ``selenium-server-standalone``):

* http://docs.seleniumhq.org/download/

You'll want to put this somewhere relatively safe (e.g. not /tmp), and remember where you put it for later.

Configure the VNC server
------------------------

If it isn't already there, create a ``.vnc`` directory in your home directory::

    $ mkdir ~/.vnc

Set a password
^^^^^^^^^^^^^^

Using the ``vncpasswd`` utility, enter your desired vnc password and save it to a file::

    $ vncpasswd ~/.vnc/passwd

The ``~/.vnc/passwd`` file stores an obfuscated version of the password entered, so you'll either want to use a memorable password or write the password down. Also, passwords longer than 8 characters will be truncated. More on this [below](Selenium-over-VNC#security).

Configure the startup script
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create or modify ``~/.vnc/xstartup``. This script is run inside the VNC server, and bootstraps the environment. It must be executable, and needs to do the following things:

* If using chrome/chromdriver, configure the ``$PATH`` environment variable so that the selenium server can find the ``google-chrome`` and ``chromedriver`` binaries
* Start the window manager (fluxbox)
* Start the selenium server in a terminal window (xterm, selenium-server-standalone-VERSION.jar)

Here's an example script that does those things:

.. code-block:: bash

    #!/bin/sh

    # Set up the environment so selenium can find everything it might want (namely chrome and chromedriver)
    export PATH="/path/to/google/chrome/directory/:/path/to/chromdriver/directory:$PATH"

    # Start the window manager
    fluxbox &

    # Start the selenium server
    xterm -maximized -e java -jar /path/to/selenium-server-standalone-VERSION.jar -ensureCleanSession -trustAllSSLCertificates &

Important things:
* The script **MUST** start with `#!/bin/sh` (or your shell shebang of choice).
* The script **MUST** be executable (`chmod +x ~/.vnc/xstartup`)

Start the server
^^^^^^^^^^^^^^^^

.. code-block:: bash

    $ vncserver :99

This will start a local VNC server, listening on display 99 and port 5999. The string ':99' is all you should need to enter into connection prompts to connect to VNC display 99. This example uses :99, but any other reasonable display number can be used throughout this guide. This server will use the password stored in ``~/.vnc/passwd``.

View your new desktop
^^^^^^^^^^^^^^^^^^^^^

To connect to the server, there are a few tools that you can use. GNOME has a built-in VNC viewer called ``vinagre``, and tigervnc also provides one. Make sure at least one of these is installed (package names are ``vinagre`` and ``tigervnc``), and then connect to the VNC server. Both tools have graphical and command-line interfaces.

To connect using either command-line tool, pass the display number as the first argument::

    $ vncviewer :99
    # -or-
    $ vinagre :99

Enter the VNC password that you set [above](Selenium-over-VNC#set-a-password). Once connected, you should see your selenium server running in a maximized xterm window.

Help for the graphical interfaces to these tools is provided by the tools themselves, but they're pretty straightforward.

Configuring the selenium client
-------------------------------

In your existing test environment, you presumably have a pytest.ini file, with a ``--driver`` argument in its addopts option. This informs the ``py.test mozwebqa`` plugin to start a selenium server and use it. We need to change this to use the remote selenium server now running inside your VNC server.

To do this, you need to replace the ``--driver`` argument with ``--browsername`` and specify the target platform. For Fedora, the platform would be ``LINUX``, but selenium recognizes any of the following (possibly more).

* WINDOWS
* XP
* VISTA
* MAC
* LINUX
* UNIX

For example, in your pytest.ini file, you need to change this::

  > addopts = **--driver=chrome** --credentials=credentials.yaml --untrusted

to this::

  > addopts = **--browsername=chrome --platform=LINUX** --credentials=credentials.yaml --untrusted

Security
--------

Simply put, VNC isn't very secure. Its connections aren't encrypted, and its passwords can only be a max of 8 characters long. For this reason, I recommend having the VNC server bind to the loopback interface. Fortunately, this is easily done by passing the '-localhost' flag to vncserver, like this::

    $ vncserver :99 -localhost

No changes need to be made in the way clients are told to connect to support this change, but it prevents other users from connecting to and interacting with this VNC session remotely.

Recording
---------

The ``recordmydesktop`` utility can be used to record test interactions for demonstration or review. Continuing with display :99 for this example, recordmydesktop can be invoked like this::

    $ recordmydesktop --display :99 --fps 60 -o outfile.ogv

In addition to specifying ``--display :99``, ``--fps 60`` is passed to ensure no steps are missed in the recording. rescordmydesktop's default framerate has shown to be a little too low to accurately capture all of the actions taken in a test run. Finally, ``-o`` is passed to specify the output file.

To record test runs in one shot, the following pattern can be followed (changing the py.test invocation as needed, of course)::

    $ recordmydesktop --display :99 --fps 60 -o test_label.ogv & py.test -k test_label --highlight; pkill recordmydesktop
