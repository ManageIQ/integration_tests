Appliances in containers
========================

This original testing suite was designed around appliances so testing of the docker container of
ManageIQ is naturally trying to mimic the original environment as much as possible in order to keep
the differences minimal. So for testing the container there are a couple of prerequisities:

* A VM with docker (Preferably Fedora, RHEL/Centos, ...)
* Docker image pulled into the VM
* A script called ``cfme-start`` which will ensure these things:

  * Runs the docker container with CFME (with the right version)
  * Maps ports 80, 443, 5432 directly to the VM's ports so HTTP(S) and PostgreSQL are publicly
    accessible
  * Maps the ``/share`` folder in the VM as ``/share`` folder in the container.

The script must be accessible as a general command, so it should preferably live eg. in
``/usr/local/bin/`` and be ``chmod +x``.

You then just templatize the VM and you can reuse it. There is a Sprout support coming.

Finally, you have to put ``container`` in the ``env.yaml`` so it looks something like this:

.. code-block:: yaml

    base_url: https://1.2.3.4/
    container: cfme
    whatever: else_is_required

The ``container`` key's values is the name of the container deployed by ``cfme-start``.

When you are done with all these steps, you are good to go with running the tests against it! And
do not forget that because of lack of the SSH daemon in the container, you are not able to use
the SCP directly like the :py:class:`utils.ssh.SSHTail` does, but only through the wrapper methods
:py:meth:`utils.ssh.SSHClient.put_file` and :py:meth:`utils.ssh.SSHClient.get_file`. It would work,
but it would only get you to the host VM, not into the container. The aforementioned wrapper
methods work by copying the file through shared directory.
