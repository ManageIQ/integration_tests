import attr
from dynaconf import settings
from yaycl import AttrDict


@attr.s
class ConfigDataWrapper(object):
    """A wrapper for credentials"""
    config = attr.ib(default=AttrDict())
    env = attr.ib(default='cfme-qe-test-envs')

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __getattr__(self, key):
        with settings.using_env(self.env):
            self.config = AttrDict(settings.as_dict()[key.upper()])
            return self.config


@attr.s
class CredsWrapper(object):
    """A wrapper for credentials"""
    credential = attr.ib(default=AttrDict())

    def __getitem__(self, env):
        return self.__getattr__(env)

    def __getattr__(self, env):
        with settings.using_env(env):
            self.credential = AttrDict(settings.as_dict())
            return self.credential


cfme_data = ConfigDataWrapper()
credentials = CredsWrapper()
