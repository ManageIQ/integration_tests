from cfme.fixtures import pytest_selenium as sel


class Topology(object):

    def __init__(self, name):
        self.name = name
        self.provider = 'Middleware'

    def nav_to_topology_view(self):
        sel.force_navigate('middleware_topology', context={
            'topology': self, 'provider': self.provider})
