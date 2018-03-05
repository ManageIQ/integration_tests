Sprout Deployment instructions
==============================

RHEL/Fedora (and compatible) systems supported.

First, these packages need to be installed:

.. code-block:: bash

    sudo yum install python-virtualenv git gcc postgresql-devel postgresql-server libxml2-devel libxslt-devel zeromq3-devel libcurl-devel redhat-rpm-config gcc-c++ openssl-devel libffi-devel python-devel python-psycopg2 redis memcached libselinux-python libsemanage-python freetype-devel libpng-devel

If you want to deploy Sprout for real, install ``nginx`` as well. For your messing around it is not necessary. Same with ``postgres``, for local fiddling SQlite works well.

If you use postgres, set the ``pg_hba.conf`` (probably in ``/var/lib/pgsql/data/`` once you have postgres initialized) like this:

.. code-block::

    local all all trust
    host all all 127.0.0.1/32 trust
    host all all ::1/128 trust

Check out this repository somewhere, get hold of the CFME QE yamls **and the yaml key** and `set your repo according to this document <http://cfme-tests.readthedocs.io/getting_started.html#obtaining-what-you-need-project-setup>`_. You don't have to set up Selenium.

Additionally to the steps taken in the guide, link the ``$YAML_DIR/sprout/cfme_data.local.yaml`` as ``$THISREPO/conf/cfme_data.local.yaml``. It contains the providers used exclusively for Sprout.

Make sure the dependencies of the project are installed, usually facilitated with the quickstart script. **ENSURE** you use a virtualenv for all operations with Sprout now!. There are additional requirements in this exact folder ``sprout/``. Install them as well. If you update project requirements, you need then to install Sprout requirements as well.

Create a ``local_settings.py`` file in ``sprout/sprout/``. You should set up the database connection if not using SQlite, refer to Django documentation regarding that. You may override the settings from ``settings.py``. **MAKE SURE** the ``memcached`` and ``redis`` ports are set correctly, otherwise you may see errors or glitches. Make sure that you set up ``STATIC_ROOT`` for real deployment to a folder which can be served by nginx (more on that later).

``HUBBER_URL`` also has to be set to point to HUBBER (``http://w.x.y.z/trackerbot``) so Sprout can start pulling informations and populate the database.

Now, since everything is ready, you can prepare the database:

.. code-block:: bash

    ./manage.py migrate

Then, you need a superuser

.. code-block:: bash

    ./manage.py createsuperuser

For developing the user interface, run Django server like this:

.. code-block:: bash

    DJANGO_DEBUG=true python manage.py runserver --noreload

Because our configuration behaves badly, ``--noreload`` needs to be used which necessitates restarting the server in case you change python files. If you change the templates or other static files, it is not necessary.

Remember to create at least one group and make sure each user is at least in one group. Make sure the providers get assigned to groups as well. No group means the provider will not be visible for anyone except superusers.

Logserver
=========

Sprout uses a multi-threaded log server that collects logs from all Sprout processes and saves them in a directory structure. This has the effect that every model and every worker task have their own log file.

To run it:

.. code-block::

    ./logserver.py

After running some code, check the log directory (eg. ``tree log/``) and you will see the structure.

Celery workers
==============

To start the celery workers, use this command:

.. code-block:: bash

    ./celery_runner worker --app=sprout.celery:app --concurrency=N --loglevel=INFO -Ofair

Where ``N`` is the number of workers to launch.

Because Sprout workers do a lot of I/O and not much of hard calculations, feel free to overcommit.

Production Sprout has more than ``8 * Ncores`` workers + 8 Gunicorn UI workers and for most of the time it works fine.

Sometimes a lot of tasks come together and swarm the workers, but give it some time and it will get fixed by itself.

Workers do not have to be started for UI to work, since UI just generates tasks (which are not consumed), but that implies redis must be running, otherwise you will get errors.


Celery Beat scheduler
=====================

Periodical tasks are scheduled by Celery Beat. To run it:

.. code-block:: bash

    ./celery_runner beat --app=sprout.celery:app


Celery Flower
=============

To see the current state of workers, you can run the Celery Flower:

.. code-block:: bash

    ./celery_runner flower --app=sprout.celery:app

Celery Flower runs on port 5555 and displays various stats about the "cluster" of workers.

Production UI
=============

To start the production UI using Gunicorn:

.. code-block:: bash

    gunicorn --bind 127.0.0.1:8000 -w N --access-logfile access.log --error-logfile error.log sprout.wsgi:application


Where N is the number of workers to serve the pages. ``Ncores - 1`` should be a good start.

Remember Gunicorn does not serve static files, you need nginx to do it for you. The nginx configuration file may look like this:

.. code-block::

    # sprout.conf

    # configuration of the server
    server {
        # the port your site will be served on
        listen      80;
        # the domain name it will serve for
        server_name hostname_of_the_server;
        charset     utf-8;
        #error_page 502 503 /etc/nginx/sprout-not-here.html;

        # max upload size
        client_max_body_size 75M;   # adjust to taste

        # Django media
        location /media/  {
            alias /var/www/sprout/media/;  # your Django project's media files - amend as required
        }

        location /static/ {
            alias /var/www/sprout/static/; # Must correspond to STATIC_ROOT
        }
        
        # Finally, send all non-media requests to the Django server.
        location / {
            proxy_pass http://127.0.0.1:8000;  # Assuming default gunicorn config
            proxy_set_header X-Forwarded-Host $server_name;
            proxy_set_header X-Real-IP $remote_addr;
            add_header P3P 'CP="ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV"';
        }
    }

Remember to set the correct SElinux boolean: ``setsebool -P httpd_can_network_connect on``.

Then you also need to collect all static files:

.. code-block:: bash

    ./manage.py collectstatic


Live update process
===================

Sprout supports a zero-downtime seamless live update process unless migrations are present. Short outage of the front-end happens when migrations have to be applied, BUT the integration_tests' Sprout client can wait for up to 1 minute in this case which - unless it explodes - is way longer than the usual stop, migrate, start process takes.

In case of change only to the UI part of sprout (eg. not tasks, ...) and no migrations are pending:

.. code-block:: bash

    kill -HUP $GUNICORN_PID

This is unnoticeable to the users.

If any migration is pending, you need to shut Gunicorn down (``SIGINT``), run the migrations and then start it again.

Remember to collect the static files after any update to them.

Workers can be stopped by sending ``SIGTERM`` signal to the worker main process. This triggers a graceful shutdown. Workers no longer accept new tasks and end after finishing the current task. If some workers seem to be stuck, you may send a ``SIGINT`` to the main process to trigger a less graceful but still clean exit. You can do that multiple times. Use ``SIGKILL`` only as the last resort as it **WILL** cause a disruption. Multiple SIGINTs usually work out fine.

The other parts of Sprout (Beat, Flower, Logserver) can be stopped simply by using ``SIGINT``.

It is recommended to wait for long tasks (appliance preconfiguration, template deployment, ...) to finish to have the update process as fast as possible.

It is recommended to shut Celery Beat down first, send a ``SIGTERM`` to the worker and wait for it to stop (or ``SIGINT`` for impatient :) ). That will ensure the smoothest worker shutdown.
