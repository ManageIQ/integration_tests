import os
from collections import OrderedDict

import py.path
import yaml
from yaml.loader import Loader


class OrderedYamlLoader(Loader):
    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)


class ConfigNotFoundException(Exception):
    pass


class Config(dict):
    """A dict subclass with knowledge of conf yamls and how to load them

    Also supports descriptor access, e.g. yamls.configfile
    (compared to the normal dict access, yamls['configfile'])
    """
    # Stash the exception on the class for convenience, e.g.
    # try:
    #     yamls[does_not_exist]
    # except yamls.NotFoundException
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
            return self[attr]

    def __getitem__(self, key):
        # Attempt a normal dict lookup to pull a cached conf
        try:
            return super(Config, self).__getitem__(key)
        except KeyError:
             # Cache miss, load the requested yaml
            yaml_dict = load_yaml(key)

            # Graft in local yaml updates if they're available
            try:
                local_yaml = '%s.local' % key
                local_yaml_dict = load_yaml(local_yaml)
                yaml_dict.update(local_yaml_dict)
            except ConfigNotFoundException:
                pass

            # Returning self[key] instead of yaml_dict as a small sanity check
            self[key] = yaml_dict
            return self[key]


def load_yaml(filename=None):
    # Find the requested yaml in the config dir, relative to this file's location
    # (aiming for cfme_tests/config)
    this_file = os.path.abspath(__file__)
    path = py.path.local(this_file).new(basename='../conf/%s.yaml' % filename)

    if path.check():
        with path.open() as config_fh:
            return yaml.load(config_fh, Loader=OrderedYamlLoader)
    else:
        msg = 'Unable to load configuration file at %s' % path
        raise ConfigNotFoundException(msg)
