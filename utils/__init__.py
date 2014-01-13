"""
utils.conf
----------

All YAML files stored in the ``conf/`` directory of the project are automatically parsed
and loaded by the utils.conf module on request by the `utils.conf` module. The parsed
files are exposed as importable attributes of the yaml file name in the module.amongst
a team of testers, and the other

For example, consider the ``conf/cfme_data.yaml`` file:

.. code-block:: python

    # Import utils.conf, use cfme_data with a fully qualified name
    import utils.conf
    provider = utils.conf.cfme_data['management_systems']['provider_name']


    # Access cfme_data as an attribute of conf
    from utils import conf
    provider = conf.cfme_data['management_systems']['provider_name']


    # Or just import cfme_data directly
    from utils.conf import cfme_data
    provider = .cfme_data['management_systems']['provider_name']


Local Configuration Overrides
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to loading YAML files, the `utils.conf` loader supports local override files.
This feature is useful for maintaining a shared set of config files for a team, while still
allowing for local configuration.

Take the following example YAML files:

.. code-block:: yaml

    # conf/example.yaml
    a: 'foo'
    b: 'spam'

    # conf/example.local.yaml
    a: ' bar'

When loaded by the conf loader, the 'a' key will be automatically overridden by the value
in the local YAML file::

    from utils.conf import example
    print example
    { 'a': 'bar', 'b': 'spam' }

As a more practical example, the best way to override `base_url` in the `env` config is with
a local override:

.. code-block:: yaml

    # conf/env.local.yaml
    base_url: https://10.9.8.7/

"""
