"""
classes to manage the cfme test framework configuration
"""

import os
import warnings
import yaycl


class Configuration(object):
    """
    holds the current configuration
    """
    def __init__(self):
        self.yaycl_config = None

    def configure(self, config_dir, crypt_key_file=None):
        """do the defered initial loading of the configuration
        :param config_dir: path to the folder with configuration files
        :param crypt_key_file:
            optional name of a file holding the key
            for encrypted configurationfiles

        :raises: AssertionError if called more than once

        if the `utils.conf` api is removed, the loading can be transformed to eager loading
        """

        assert self.yaycl_config is None
        if crypt_key_file and os.path.exists(crypt_key_file):
            self.yaycl_config = yaycl.Config(
                config_dir=config_dir,
                crypt_key_file=crypt_key_file)
        else:
            self.yaycl_config = yaycl.Config(config_dir=config_dir)

    def get_config(self, name):
        """returns a yaycl config object

        :param name: name of the configuration object
        """

        if self.yaycl_config is None:
            raise RuntimeError('cfme configuration was not initialized')
        return getattr(self.yaycl_config, name)


class DeprecatedConfigWrapper(object):
    """
    a wrapper that provides the old :code:``utils.conf`` api
    """
    def __init__(self, configuration):
        self.configuration = configuration

    def __getattr__(self, key):
        warnings.warn(
            'the configuration module {} will be deprecated'.format(key),
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.configuration.get_config(key)

    def __getitem__(self, key):
        warnings.warn(
            'the configuration module {} will be deprecated'.format(key),
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.configuration.get_config(key)

    def __delitem__(self, key):
        # used in bad logging
        warnings.warn('clearing configuration is bad', stacklevel=2)

        del self.configuration.yaycl_config[key]

# for the initial usage we keep a global object
# later on we want to replace it
global_configuration = Configuration()
