class Endpoint(object):
    def __init__(self, name, impl, owner):
        """Class name setting"""
        self.name = name
        self._impl = impl
        self.owner = owner

    @property
    def impl(self):
        # ** Some implementations are callable, some are properties that we don't want to call
        # ** until we are ready to use them. This helps here. Nice!
        if callable(getattr(self.owner, self._impl)):
            return self.impl()
        else:
            return self.impl
