import os

import py.path
import yaml
from yaml.loader import Loader


class YamlConfigLoader(Loader):
    # Override the root yaml node to be a RecursiveUpdateDict
    def construct_yaml_map(self, node):
        data = RecursiveUpdateDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)
# Do the same for child nodes of the yaml mapping type
YamlConfigLoader.add_constructor('tag:yaml.org,2002:map', YamlConfigLoader.construct_yaml_map)


class ConfigNotFoundException(Exception):
    pass


class Config(dict):
    """A dict subclass with knowledge of conf yamls and how to load them

    Also supports descriptor access, e.g. conf.configfile
    (compared to the normal dict access, conf['configfile'])
    """
    # Stash the exception on the class for convenience, e.g.
    # try:
    #     conf[does_not_exist]
    # except conf.NotFoundException
    #     ...
    NotFoundException = ConfigNotFoundException

    # Support for descriptor access, e.g. instance.attrname
    # Note that this is only on the get side, for support of nefarious things
    # like setting and deleting, use the normal dict interface.
    def __getattribute__(self, attr):
        # Attempt normal object attr lookup; delegate to the dict interface if that fails
        try:
            return super(Config, self).__getattribute__(attr)
        except AttributeError:
            value = self[attr]
            if isinstance(value, dict) and not isinstance(value, self.__class__):
                return self.__class__(value)
            else:
                return value

    def __getitem__(self, key):
        # Attempt a normal dict lookup to pull a cached conf
        try:
            return super(Config, self).__getitem__(key)
        except KeyError:
             # Cache miss, load the requested yaml
            yaml_dict = self.__class__(load_yaml(key))

            # Graft in local yaml updates if they're available
            try:
                local_yaml = '%s.local' % key
                local_yaml_dict = load_yaml(local_yaml)
                yaml_dict.update_only_new(local_yaml_dict)
            except ConfigNotFoundException:
                pass

            # Returning self[key] instead of yaml_dict as a small sanity check
            self[key] = yaml_dict
            return self[key]

    def update_only_new(self, new_data):
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

        Returns:
            self
        """
        for key, value in new_data.iteritems():
            if key not in self:
                self[key] = value
            elif not isinstance(value, dict):
                self[key] = value
            else:
                # It must be instance of dict or Config so we make sure it's Config
                new = self.__class__(value)
                # If the key present is not a Config, we must convert it to be able to _only_new()
                try:
                    if not isinstance(self[key], self.__class__):
                        self[key] = self.__class__(self[key])
                except TypeError:
                    # The old value is not a dictionary (conversion failed)
                    # So we will overwrite it because we update only dicts
                    self[key] = new
                else:
                    # The new value is a dictionary, so recursively update it
                    self[key].update_only_new(new)
        return self


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


def load_yaml(filename=None):
    # Find the requested yaml in the config dir, relative to this file's location
    # (aiming for cfme_tests/config)
    this_file = os.path.abspath(__file__)
    path = py.path.local(this_file).new(basename='../conf/%s.yaml' % filename)

    if path.check():
        with path.open() as config_fh:
            return yaml.load(config_fh, Loader=YamlConfigLoader)
    else:
        msg = 'Unable to load configuration file at %s' % path
        raise ConfigNotFoundException(msg)
