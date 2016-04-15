from cfme.fixtures import pytest_selenium as sel
from cfme.middleware.provider import HawkularProvider


class Topology(HawkularProvider):

    def __init__(self, name):
        self.name = name
        self.provider = self.string_name

    def nav_to_topology_view(self):
        sel.force_navigate('middleware_topology', context={'topology': self, 'provider': self.provider})