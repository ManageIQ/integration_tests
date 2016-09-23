import os
import warnings
import yaycl


class Configuration(object):
    def __init__(self):
        self.yaycl_config = None

    def configure(self, config_dir, crypt_key_file=None):
        assert self.yaycl_config is None
        if crypt_key_file and os.path.exists(crypt_key_file):
            self.yaycl_config = yaycl.Config(
                config_dir=config_dir,
                crypt_key_file=crypt_key_file)
        else:
            self.yaycl_config = yaycl.Config(config_dir=config_dir)

    def get_config(self, name):
        if self.yaycl_config is None:
            raise RuntimeError('cfme configuration was not initialized')
        return getattr(self.yaycl_config, name)


class DeprecatedConfigWrapper(object):
    def __init__(self, configuration):
        self.configuration = configuration

    def __getattr__(self, key):
        warnings.warn(
            'the configuration module %s will be deprecated' % (key,),
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.configuration.get_config(key)

    def __getitem__(self, key):
        warnings.warn(
            'the configuration module %s will be deprecated' % (key,),
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
