from dynaconf import LazySettings

from cfme.utils import path


class ConfigDataWrapper(object):
    """A wrapper for credentials"""
    def __init__(self, env='cfme-qe-test-envs'):
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


cfme_data = ConfigDataWrapper()
