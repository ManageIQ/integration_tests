"""
classes to manage the cfme test framework configuration
"""
import attr
from dynaconf import LazySettings

from cfme.utils import path


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
        # For some reason '__path__' was being received in name
        # for which we won't have valid key.
        # hence the if check below.
        if not name == '__path__':
            return self.settings[name]


@attr.s
class ConfigWrapper(object):
    configuration = attr.ib()

    def __getattr__(self, key):
        return self.configuration.get_config(key)

    def __getitem__(self, key):
        return self.configuration.get_config(key)
