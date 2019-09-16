from dynaconf import LazySettings

from cfme.utils import path


class ConfigDataWrapper(object):
    """A wrapper for credentials"""
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


cfme_data = ConfigDataWrapper()
docker = ConfigDataWrapper(env='docker')
env = ConfigDataWrapper(env='env')
gpg = ConfigDataWrapper(env='gpg')
cfme_performance = ConfigDataWrapper(env='cfme_performance')
jenkins = ConfigDataWrapper(env='jenkins')
migration_tests = ConfigDataWrapper(env='migration_tests')
perf_tests = ConfigDataWrapper(env='perf_tests')
polarion_tools = ConfigDataWrapper(env='polarion_tools')
rdb = ConfigDataWrapper(env='rdb')
supportability = ConfigDataWrapper(env='supportability')
