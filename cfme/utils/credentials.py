import attr
from dynaconf import settings
from yaycl import AttrDict


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


credentials = CredsWrapper()
