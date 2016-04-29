from cfme.fixtures import pytest_selenium as sel


class Topology(object):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def nav_to_topology_view(self):
        sel.force_navigate('middleware_topology', context={
            'topology': self, 'provider': self.provider})
