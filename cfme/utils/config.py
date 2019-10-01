"""
classes to manage the cfme test framework configuration
"""
import attr
from dynaconf import LazySettings
import os
import yaycl

from cfme.utils import path

YAML_KEYS = ['auth_data', 'cfme_data', 'cfme_performance', 'composite',
            'credentials', 'docker', 'env', 'gpg', 'hidden', 'jenkins',
            'migration_tests', 'perf_tests', 'polarion_tools', 'rdb',
            'supportability']


class ConfigData(object):
    """A wrapper for configs in yamls- reads and loads values from yaml files in conf/ dir."""
    def __init__(self, env='cfme_data'):
        self.settings = LazySettings(
            ENV_FOR_DYNACONF=env,
            INCLUDES_FOR_DYNACONF='{}/*.yaml'.format(path.conf_path.strpath),
            ROOT_PATH_FOR_DYNACONF=path.conf_path.strpath
        )

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __getattr__(self, key):
        self.config = self.settings[key.upper()]
        return self.config

    def __setitem__(self, key, value):
        """This function allows you to mimic some behavior like runtime from yaycl
            You can do following:
                from cfme.utils import conf
                conf ['env']['new_key'] = 'new_val'
                conf ['env']['new_key']
                # The new_key and its value is cached through the session
        """
        self.settings[key] = value

    def __contains__(self, key):
        return key in self.settings.as_dict() or key.upper() in self.settings.as_dict()

    def get(self, key, default=None):
        try:
            return self.__getattr__(key)
        except KeyError:
            return default


class Configuration(object):
    """
    Holds ConfigData objects in dictionary `settings`.
    """
    def __init__(self):
        self.settings = None
        self.yaycl_config = None

    def configure_creds(self, config_dir, crypt_key_file=None):
        """
        do the defered initial loading of the configuration

        :param config_dir: path to the folder with configuration files
        :param crypt_key_file: optional name of a file holding the key for encrypted
            configuration files

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

    def configure(self):
        """
        Loads all the congfigs in settings dictionary where Key is filename(without extension)
        and value is ConfigData object relevant to that file.

        Example self.settings would look like:
        {'cfme_data': <cfme.utils.config_copy.ConfigData at 0x7f2a943b14e0>,
         'env': <cfme.utils.config_copy.ConfigData at 0x7f2a943b1be0>,
         'gpg': <cfme.utils.config_copy.ConfigData at 0x7f2a943b1cc0>,
         ...
         ...
         'polarion_tools': <cfme.utils.config_copy.ConfigData at 0x7f2a943ad438>,
         'perf_tests': <cfme.utils.config_copy.ConfigData at 0x7f2a943ad2e8>}

        """
        if self.settings is None:
            self.settings = {
                file.basename[:-5]: ConfigData(env=file.basename[:-5])
                for file in path.conf_path.listdir() if file.basename[-5:] == '.yaml' and
                '.local.yaml' not in file.basename
            }

    def get_config(self, name):
        """returns a config object

        :param name: name of the configuration object
        """
        self.configure()
        if name in YAML_KEYS:
            if name == 'credentials' or name == 'hidden':
                return getattr(self.yaycl_config, name)
            try:
                return self.settings[name]
            except KeyError:
                # seems like config was deleted, reload
                self.settings[name] = ConfigData(env=name)
                return self.settings[name]

    def del_config(self, name):
        if self.settings:
            if name in self.settings:
                del self.settings[name]


@attr.s
class ConfigWrapper(object):
    configuration = attr.ib()

    def __getattr__(self, key):
        return self.configuration.get_config(key)

    def __getitem__(self, key):
        return self.configuration.get_config(key)

    def __delitem__(self, key):
        return self.configuration.del_config(key)


global_configuration = Configuration()
