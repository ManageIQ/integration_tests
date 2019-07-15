"""
classes to manage the cfme test framework configuration
"""
import os

import attr
import yaycl


@attr.s
class Configuration(object):
    """
    holds the current configuration

    Supports cfme.utils.conf module impersonation and lazy loading
    """
    yaycl_config = attr.ib(default=None)

    def configure(self, config_dir, key_file=None):
        """
        do the defered initial loading of the configuration

        Args:
            config_dir (str): path to the folder with configuration files
            key_file (str): optional name of file holding the key for encrypted configuration files

        :raises: AssertionError if called more than once

        if the `utils.conf` api is removed, the loading can be transformed to eager loading
        """
        self.yaycl_config = yaycl.Config(
            config_dir=config_dir,
            crypt_key_file=key_file if key_file and os.path.exists(key_file) else None,
        )
        return self.yaycl_config

    def get_config(self, name):
        """returns a yaycl config object

        :param name: name of the configuration object
        """

        if self.yaycl_config is None:
            raise RuntimeError('cfme configuration was not initialized')
        return getattr(self.yaycl_config, name)
