from cfme.fixtures import pytest_selenium as sel


class Deployment(object):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def nav_to_deployments_view(self):
        sel.force_navigate('middleware_deployments', context={
            'deployments': self, 'provider': self.provider})
