from random import choice

import pytest

from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([OpenstackInfraProvider], scope='module'),
]


ROLES = ['NovaCompute', 'Controller', 'Compute', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


@pytest.fixture(scope="module")
def roles(appliance, provider):
    collection = appliance.collections.deployment_roles.filter({'provider': provider})
    roles = collection.all()

    # TODO: remove test skip after introducing deployment role creation method.
    yield roles if roles else pytest.skip("No Roles Available")


@pytest.mark.regression
def test_host_role_association(appliance, provider, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    host_collection = appliance.collections.hosts
    hosts = host_collection.all()
    assert len(hosts) > 0
    for host in hosts:
        host.run_smartstate_analysis()

        task = appliance.collections.tasks.instantiate(
            name=f"SmartState Analysis for '{host.name}'", tab='MyOtherTasks')
        task.wait_for_finished()
        view = navigate_to(host, 'Details')
        role_name = str(view.title.text.split()[1]).translate(None, '()')
        role_name = 'Compute' if role_name == 'NovaCompute' else role_name

        try:
            role_assoc = view.entities.summary('Relationships').get_text_of('Deployment Role')
        except NameError:
            role_assoc = (view.entities.summary('Relationships').get_text_of
                ('Cluster / Deployment Role'))
        soft_assert(role_name in role_assoc, 'Deployment roles misconfigured')


@pytest.mark.regression
def test_roles_name(roles):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    for role in roles:
        role_name = role.name.split('-')[1]
        assert role_name in ROLES


@pytest.mark.regression
def test_roles_summary(roles, soft_assert):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
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


@pytest.mark.regression
def test_role_delete(roles):
    """
    Polarion:
        assignee: mnadeem
        casecomponent: Cloud
        initialEstimate: 1/4h
    """
    role = choice(roles)
    role.delete()
    view = navigate_to(role, 'AllForProvider')
    available_roles = view.entities.get_all()
    assert role not in available_roles
