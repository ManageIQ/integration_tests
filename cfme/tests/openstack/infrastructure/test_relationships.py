"""
This test can run only after overcloud cloud provider created and linked to
undercloud infra provider, need to compare the cloud providers with the
results of the relationships
"""
from utils import testgen, version
import pytest


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate'),
              pytest.mark.usefixtures("setup_provider_modscope")]


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_assigned_roles(provider):
    provider.load_details()
    assert provider.get_detail('Relationships', 'Deployment roles') > 0


def test_nodes(provider):
    provider.load_details()
    """
    todo get the list of VM's from external resource and compare
    it with result - currently not 0
    """

    assert provider.get_detail('Relationships', 'Nodes') > 0


def test_templates(provider):
    provider.load_details()
    """
    todo get the list of images/templates from external resource and compare
    it with result - currently  bigger than 0
    """

    assert provider.get_detail('Relationships', 'Templates') > 0


def test_stacks(provider):
    provider.load_details()
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert provider.get_detail('Relationships', 'Orchestration stacks') > 0
