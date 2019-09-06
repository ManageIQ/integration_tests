from dynaconf import LazySettings


class ConfigDataWrapper(object):
    """A wrapper for credentials"""
    def __init__(self, env='cfme-qe-test-envs', conf_path='conf/*.yaml'):
        self.settings = LazySettings(ENV_FOR_DYNACONF=env, INCLUDES_FOR_DYNACONF=conf_path)

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __getattr__(self, key):
        self.config = self.settings[key.upper()]
        return self.config


cfme_data = ConfigDataWrapper()
