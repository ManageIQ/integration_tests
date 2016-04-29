from cfme.fixtures import pytest_selenium as sel


class Deployments(object):

    def __init__(self, name):
        self.name = name
        self.provider = 'Middleware'

    def nav_to_deployments_view(self):
        sel.force_navigate('middleware_deployments', context={
            'deployments': self, 'provider': self.provider})
