from utils import InstanceClassMethod
from utils.log import logger


class NavigateWrap(object):
    def __init__(self, *args, **kwargs):
        self.cls = args[0]

    def __call__(self, f):
        self.cls._nav_steps[f.__name__] = f
        return f


class Navigatable(object):
    def __init__(self, *args, **kwargs):
        self.navigate = self.instance_navigate

    @InstanceClassMethod
    def navigate(self, name):
        nav_step = self._nav_steps[name](self)
        nav_step.go()

    @navigate.classmethod
    def navigate(cls, name):  # noqa
        nav_step = cls._nav_steps[name](cls)
        nav_step.go()


class NavigateStep(object):
    def __init__(self, obj):
        self.obj = obj

    def am_i_here(self):
        return False

    def go(self):
        logger.debug("NAVIGATE: Checking if already at {}".format(self.__class__.__name__))
        try:
            if self.am_i_here():
                return
        except Exception as e:
            logger.debug("NAVIGATE: Exception raised {} checking if already at {}".format(
                e, self.__class__.__name__))
        if hasattr(self, 'prerequisite'):
            logger.debug("NAVIGATE: Performing prerequisite step")
            if isinstance(self.prerequisite, basestring):
                self.obj.navigate(self.prerequisite)
            else:
                self.prerequisite()
        logger.debug("NAVIGATE: Heading to destination {}".format(self.__class__.__name__))
        self.step()
