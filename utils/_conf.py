from warnings import catch_warnings, warn

import yaml
from yaml.loader import Loader

from utils.path import conf_path


class YamlConfigLoader(Loader):
    # Override the root yaml node to be a RecursiveUpdateDict
    def construct_yaml_map(self, node):
        data = RecursiveUpdateDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)
# Do the same for child nodes of the yaml mapping type
YamlConfigLoader.add_constructor('tag:yaml.org,2002:map', YamlConfigLoader.construct_yaml_map)


class ConfigNotFound(UserWarning):
    pass


class Config(dict):
    # This becomes the docstring for utils.conf
    # Supressing or selectively rewriting the dict method docstrings would be handy
    """Configuration YAML loader and cache

    All YAML files stored in the ``conf/`` directory of the project are automatically parsed
    and loaded on request by this module. The parsed files are exposed as importable attributes
    of the yaml file name in the module.

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
        provider = cfme_data['management_systems']['provider_name']


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

    .. note::

        This module contains dynamic attributes. As a result, its functionality can be found in
        the source as ``utils._conf.Config``

    Inherited methods
    ^^^^^^^^^^^^^^^^^

    Being a ``dict`` subclass, the following dictionary methods can also be used to manipulate
    ``utils.conf`` at runtime. :py:func:`clear` is particularly useful as a means to trigger
    a reload of config files.

    """
    def __init__(self, path):
        # stash a path to better impersonate a module
        self.path = path

    @property
    def __path__(self):
        # and return that path when asked
        return self.path

    # Support for descriptor access, e.g. instance.attrname
    # Note that this is only on the get side, for support of nefarious things
    # like setting and deleting, use the normal dict interface.
    def __getattribute__(self, attr):
        # Attempt normal object attr lookup; delegate to the dict interface if that fails
        try:
            return super(Config, self).__getattribute__(attr)
        except AttributeError:
            return self[attr]

    def __getitem__(self, key):
        # Attempt a normal dict lookup to pull a cached conf
        try:
            return super(Config, self).__getitem__(key)
        except KeyError:
             # Cache miss, load the requested yaml
            yaml_dict = load_yaml(key)

            # Graft in local yaml updates if they're available
            with catch_warnings():
                local_yaml = '%s.local' % key
                local_yaml_dict = load_yaml(local_yaml, warn_on_fail=False)
                yaml_dict.update(local_yaml_dict)

            # Returning self[key] instead of yaml_dict as a small sanity check
            self[key] = yaml_dict
            return self[key]


class RecursiveUpdateDict(dict):
    def update(self, new_data):
        """ More intelligent dictionary update.

        This method changes just data that have been changed. How does it work?
        Imagine you want to change just VM name, other things should stay the same.

        Original config:
        something:
            somewhere:
                VM:
                    a: 1
                    b: 2
                    name: qwer
                    c: 3

        Instead of copying the whole part from original to the override with just 'name' changed,
        you will write this:

        something:
            somewhere:
                VM:
                    name: tzui

        This digging deeper affects only dictionary values. Lists are unaffected! And so do other
        types.

        Args:
            new_data: Update data.
        """
        for key, value in new_data.iteritems():
            if isinstance(value, type(self)) and key in self:
                type(self).update(self[key], value)
            else:
                self[key] = new_data[key]


def load_yaml(filename=None, warn_on_fail=True):
    # Find the requested yaml in the config dir, relative to this file's location
    # (aiming for cfme_tests/config)
    path = conf_path.join('%s.yaml' % filename)

    if path.check():
        with path.open() as config_fh:
            return yaml.load(config_fh, Loader=YamlConfigLoader)

    if warn_on_fail:
        msg = 'Unable to load configuration file at %s' % path
        warn(msg, ConfigNotFound)

    return {}
