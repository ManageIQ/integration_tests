# -*- coding: utf-8 -*-
from collections import defaultdict
from warnings import catch_warnings, warn

import copy
import hashlib
import os
import yaml
from yaml.loader import Loader
from Crypto.Cipher import AES

from utils.path import conf_path, project_path


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

    .. note::

        Special care has been taken to ensure that all objects are mutated, rather than replaced,
        so all names will reference the same config object.

        All objects representing config files (attributes or items accessed directly from the conf
        module) will be some type of :py:class:`dict <python:dict>`. Attempting to make such a
        config object be anything other than a ``dict`` (or decscendant of ``dict``) will probably
        break everything and should not be attempted::

            from utils import conf
            # Don't do this...
            conf.cfme_data = 'not a dict'
            # ...or this.
            conf['env'] = ['also', 'not', 'a', 'dict']

        No care whatsoever has been taken to ensure thread-safety, so if you're doing crazy threaded
        things with the conf module you should manage your own locking when making any runtime conf
        changes.

    Local Configuration Overrides
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    In addition to loading YAML files, the :py:mod:`utils.conf` loader supports local override
    files. This feature is useful for maintaining a shared set of config files for a team, while
    still allowing for local configuration.

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

    Runtime Overrides
    ^^^^^^^^^^^^^^^^^

    Sometimes writing to the config files is an inconvenient way to ensure that runtime changes
    persist through configuration cache clearing. As above, changing the ``base_url`` of the
    current appliance is the most common example.

    In these cases, using the runtime overrides dictionary will accomplish this. The runtime
    overrides dictionary mimics the layout of the conf module itself, where configuration file
    names are keys in the runtime overrides dictionary. So, for example, to update the base_url
    in a way that will persist clearing of the cache, the following will work::

        from utils import conf
        conf.runtime['env']['base_url'] = 'https://4.3.2.1/'
        print conf.env['base_url']
        https://4.3.2.1

    Inherited methods
    ^^^^^^^^^^^^^^^^^

    Being a :py:class:`dict <python:dict>` subclass, dictionary methods can also be used to
    manipulate ``utils.conf`` at runtime. :py:meth:`clear <python:dict.clear>` is particularly
    useful as a means to trigger a reload of all config files. These changes won't persist a cache
    clear, however, so using the runtime overrides mechanism is recommended.

    .. note::

        This module contains dynamic attributes. As a result, its functionality can be found in
        the source as :py:class:`utils._conf.Config`

    Encryption
    ^^^^^^^^^^

    Encrpyted yamls are supported. Encrypted yamls are expected to have the ``eyaml`` extension.

    The conf loader will look for the encryption key in these places:

    - The value of the CFME_TESTS_KEY environment variable
    - The contents of the file specified with the CFME_TESTS_KEY_FILE environment variable
    - The contents of ``.yaml_key`` in the project root (cfme_tests)

    ..note::

        If an unencrypted and an encrypted yaml of the same name exist in conf, the unencrypted
        YAML will be loaded and a message will be printed notifying the user.

    """
    def __init__(self, path):
        # stash a path to better impersonate a module
        self.path = path
        self._runtime = ConfigTree()

    @property
    def __path__(self):
        # and return that path when asked
        return self.path

    def _runtime_overrides(self):
        return self._runtime

    def _set_runtime_overrides(self, overrides_dict):
        # Writing to the overrides_dict clears cached conf,
        # ensuring new value on next access
        for key in overrides_dict:
            if key in self:
                self[key].clear()
        self._runtime.update(overrides_dict)

    def _del_runtime_overrides(self):
        self._runtime.clear()

    def save(self, key):
        """Write out an in-memory config to the conf dir

        Warning: This will destroy any formatting or ordering that existed in the original yaml

        """
        conf_file = conf_path.join('%s.yaml' % key).open('w')
        yaml.dump(getattr(self, key), conf_file, default_flow_style=False)

    runtime = property(_runtime_overrides, _set_runtime_overrides, _del_runtime_overrides)

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
            # Cache miss, populate this conf key
            # Call out to dict's setitem here since this is the only place where we're allowed to
            # create a new key and we want the default behavior instead of the override below
            super(Config, self).__setitem__(key, RecursiveUpdateDict())
            self._populate(key)
            return self[key]

    def __setitem__(self, key, value):
        self[key].clear()
        self[key].update(value)

    def __delitem__(self, key):
        self[key].clear()
        self._populate(key)

    def _inherit(self, key, obj, path, updates=None):
        """Recurses through an object looking for 'inherit' clauses and replaces them with their
        real counterparts. In the case of a dict, the inherit clause remains, in the case of
        anything else, a replacement occurs such that:

        sim5:
          key: value
          newkey: newvalue

        sim6:
          tags:
            - tag1
            - tag2
        sim7:
          inherit: management_systems/sim5
          test:
              tags:
                  inherit: management_systems/sim6/tags

        Will produce the following output if requesting management_systems/sim7

          inherit: management_systems/sim5
          key: value
          newkey: newvalue
          test:
              tags:
                  - tag1
                  - tag2
        """
        if not updates:
            updates = RecursiveUpdateDict()
        if 'inherit' in obj:
            inherited_object = copy.deepcopy(self[key].tree_get(obj['inherit'].split('/')))
            inheritance_updates = RecursiveUpdateDict().tree_set(path, inherited_object)
            updates.update(inheritance_updates)
        for ob in obj:
            npath = path + [ob]
            if ob == 'inherit':
                continue
            if isinstance(obj[ob], RecursiveUpdateDict):
                recurse_inherit = self._inherit(key, obj[ob], npath, updates)
                updates.update(recurse_inherit)
            else:
                original_values = RecursiveUpdateDict().tree_set(npath, obj[ob])
                updates.update(original_values)
        return updates

    def _populate(self, key):
        yaml_dict = load_yaml(key)

        # Graft in local yaml updates if they're available
        with catch_warnings():
            local_yaml = '%s.local' % key
            local_yaml_dict = load_yaml(local_yaml, warn_on_fail=False)
            if local_yaml_dict:
                yaml_dict.update(local_yaml_dict)

        # Graft on the runtime overrides
        yaml_dict.update(self.runtime.get(key, {}))
        self[key].update(yaml_dict)

        self[key].update(self._inherit(key, self[key], []))

    def clear(self):
        # because of the 'from conf import foo' mechanism, we need to clear each key in-place,
        # and reload the runtime overrides. Once a key is created in this dict, its value MUST NOT
        # change to a different dict object.
        for key in self:
            # clear the conf dict in-place
            self[key].clear()
            self._populate(key)


class ConfigTree(defaultdict):
    """A tree class that knows to clear the config when mutated

    This is needed to ensure runtime overrides persist though conf changes

    """
    def __init__(self, *args, **kwargs):
        super(ConfigTree, self).__init__(type(self), *args, **kwargs)

    @property
    def _sup(self):
        return super(ConfigTree, self)

    def __setitem__(self, key, value):
        self._sup.__setitem__(key, value)
        self._clear_conf()

    def __delitem__(self, key):
        self._sup.__delitem__(key)
        self._clear_conf()

    def update(self, other):
        self._sup.update(other)
        self._clear_conf()

    def _clear_conf(self):
        from utils import conf
        conf.clear()


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

    def tree_get(self, path):
        # Given a path, and a dict objct, this function will traverse the dict using the elements
        # in the path and return the result, thanks @benbacardi
        return reduce(lambda x, y: x[y], path, self)

    def tree_set(self, path, setter):
        # Given a path, and a dict objct, this function will traverse the dict using the elements
        # in the path and set the leaf to setter. If nodes do not exist, it will create them as
        # RecursiveUpdateDict() objects
        path = path[:]
        worker = self
        while len(path) > 1:
            new_index = path.pop(0)
            if new_index not in worker:
                worker[new_index] = RecursiveUpdateDict()
            worker = worker[new_index]
        worker[path[0]] = setter
        return self


def get_aes_key():
    """Retrieve the AES key used for encryption/decryption.

    Looks in the environment variable and if it does not find it, looks in .yaml_key file located
    in the project root.
    """
    if "CFME_TESTS_KEY" in os.environ:
        data = os.environ["CFME_TESTS_KEY"].strip()
    else:
        if "CFME_TESTS_KEY_FILE" in os.environ:
            key_file = os.environ["CFME_TESTS_KEY_FILE"].strip()
        else:
            key_file = project_path.join(".yaml_key").strpath

        try:
            with open(key_file, "r") as f:
                data = f.read().strip()
        except IOError:
            data = None
    return hashlib.sha256(data).digest() if data is not None else None


def load_yaml(filename=None, warn_on_fail=True):
    conf = None

    filename_unencrypted = conf_path.join('{}.yaml'.format(filename))
    filename_encrypted = conf_path.join('{}.eyaml'.format(filename))

    # Find the requested yaml in the conf dir
    if filename_unencrypted.check():
        # If there's an unencypted credentials.yaml, use it.
        if filename_encrypted.check():
            print ('Encrypted and unencrypted {} present, '
                'using unencrypted yaml'.format(filename_unencrypted.basename))
        with filename_unencrypted.open() as config_fh:
            conf = yaml.load(config_fh, Loader=YamlConfigLoader)
    elif filename_encrypted.check():
        # If the unencrypted file didn't exist, try to use the encrypted file
        key = get_aes_key()
        if not key:
            raise Exception("Cannot decrypt {} (no key)!".format(filename_encrypted.basename))

        cipher = AES.new(key, AES.MODE_ECB)
        with filename_encrypted.open("r") as encrypted:
            conf = yaml.load(cipher.decrypt(encrypted.read()).strip())

    if isinstance(conf, dict):
        return conf

    if warn_on_fail:
        msg = 'Unable to load configuration file at %s' % filename_unencrypted
        warn(msg, ConfigNotFound)


def encrypt_yaml(filename):
    filename_unencrypted = conf_path.join('{}.yaml'.format(filename))
    filename_encrypted = conf_path.join('{}.eyaml'.format(filename))

    if filename_unencrypted.check():
        # Decrypt the file
        key = get_aes_key()
        if key is None:
            raise Exception(
                "Cannot encrypt config file {} - no key provided!".format(filename))
        cipher = AES.new(key, AES.MODE_ECB)
        with filename_unencrypted.open("r") as unencrypted:
            with filename_encrypted.open("w") as encrypted:
                data = unencrypted.read()
                while len(data) % len(key) > 0:
                    data += " "  # Padding with spaces, will be rstripped after load
                encrypted.write(cipher.encrypt(data))
    else:
        raise Exception("No such file!")
