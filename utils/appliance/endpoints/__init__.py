# class EndpointException(Exception):
#    pass


class Endpoint(object):
    def __init__(self, name, impl, owner):
        """Class name setting"""
        self.name = name
        self._impl = impl
        self.owner = owner

    @property
    def impl(self):
        if callable(getattr(self.owner, self._impl)):
            return self.impl()
        else:
            return self.impl

# class EndpointManager(object):
#    def __init__(self):
#        self._endpoints = {}

#    def add(self, name, obj):
#        self._endpoints[name] = obj

#    def __getattr__(self, name):
#        try:
#            return self._endpoints[name]
#        except KeyError:
#            raise EndpointException('Endpoint {} not known'.format(name))
