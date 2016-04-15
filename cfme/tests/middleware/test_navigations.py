
import pytest

from utils import testgen

from cfme.middleware.servers import Servers
from cfme.middleware.deployments import Deployments
from cfme.middleware.topology import Topology


### This test case is intended for knowledge/idea sharing only!! ###

def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.middleware_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.mark.usefixtures('has_no_middleware_providers')
def test_hawkular_crud(provider):

    hawkServers = Servers(provider.name)
    hawkServers.nav_to_servers_view()
    hawkServers.nav_to_detailed_view()

    hawkDeployments = Deployments(provider.name)
    hawkDeployments.nav_to_deployments_view()

    hawkTopology = Topology(provider.name)
    hawkTopology.nav_to_topology_view()

    hawkServers.nav_to_servers_view()
