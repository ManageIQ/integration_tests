from cfme.fixtures import pytest_selenium as sel
from cfme.middleware.provider import HawkularProvider


class Deployments(HawkularProvider):

    def __init__(self, name):
        self.name = name
        self.provider = self.string_name

    def nav_to_deployments_view(self):
        sel.force_navigate('middleware_deployments', context={'deployments': self, 'provider': self.provider})