from cfme.common import TopologyMixin
from cfme.fixtures import pytest_selenium as sel


class MiddlewareTopology(TopologyMixin):

    @classmethod
    def load_topology_page(cls):
        sel.force_navigate('middleware_topology')
