import pytest
from random import choice

from cfme.configure.tasks import is_host_analysis_finished
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


ROLES = ['NovaCompute', 'Controller', 'Compute', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


@pytest.yield_fixture(scope="module")
def roles(appliance, provider):
    collection = appliance.collections.deployment_roles.filter({'provider': provider})
    roles = collection.all()

    # TODO: remove test skip after introducing deployment role creation method.
    yield roles if roles else pytest.skip("No Roles Available")


def test_host_role_association(appliance, provider, soft_assert):
    host_collection = appliance.collections.hosts
    hosts = host_collection.all(provider)
    assert len(hosts) > 0
    for host in hosts:
        host.run_smartstate_analysis()

        wait_for(is_host_analysis_finished, [host.name], delay=15,
                 timeout="10m", fail_func=host.browser.refresh)
        view = navigate_to(host, 'Details')
        role_name = str(view.title.text.split()[1]).translate(None, '()')
        role_name = 'Compute' if role_name == 'NovaCompute' else role_name

        try:
            role_assoc = view.entities.relationships.get_text_of('Deployment Role')
        except NameError:
            role_assoc = view.entities.relationships.get_text_of('Cluster / Deployment Role')
        soft_assert(role_name in role_assoc, 'Deployment roles misconfigured')


def test_roles_name(roles):
    for role in roles:
        role_name = role.name.split('-')[1]
        assert role_name in ROLES


def test_roles_summary(roles, soft_assert):
    err_ptrn = '{} are shown incorrectly'

    for role in roles:
        view = navigate_to(role, 'DetailsFromProvider')

        for v in ('Nodes', 'Direct VMs', 'All VMs'):
            res = view.entities.relationships.get_text_of(v)
            soft_assert(res.isdigit(), err_ptrn.format(v))

        for v in ('Total CPUs', 'Total Node CPU Cores'):
            res = view.entities.total_for_node.get_text_of(v)
            soft_assert(res.isdigit() and int(res) > 0, err_ptrn.format(v))

        total_cpu = view.entities.total_for_node.get_text_of('Total CPU Resources')
        soft_assert('GHz' in total_cpu, err_ptrn.format('Total CPU Resources'))
        total_memory = view.entities.total_for_node.get_text_of('Total Memory')
        soft_assert('GB' in total_memory, err_ptrn.format('Total Memory'))

        for v in ('Total Configured Memory', 'Total Configured CPUs'):
            res = view.entities.total_for_vm.get_text_of(v)
            soft_assert(res, err_ptrn.format(v))


def test_role_delete(roles):
    role = choice(roles)
    role.delete()
    view = navigate_to(role, 'AllForProvider')
    available_roles = view.entities.get_all()
    assert role not in available_roles
