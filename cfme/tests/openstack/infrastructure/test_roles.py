import pytest
from random import choice
from selenium.common.exceptions import NoSuchElementException

from cfme.configure.tasks import is_host_analysis_finished
from cfme.infrastructure.deployment_roles import DeploymentRoles
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import flash, Quadicon, summary_title, toolbar
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.wait import wait_for


pytest_generate_tests = testgen.generate([OpenstackInfraProvider],
                                         scope='module')
pytestmark = [pytest.mark.usefixtures("setup_provider_modscope")]


ROLES = ['NovaCompute', 'Controller', 'Compute', 'BlockStorage', 'SwiftStorage',
         'CephStorage']


def test_host_role_association(provider, soft_assert):
    navigate_to(provider, 'ProviderNodes')
    names = [q.name for q in list(Quadicon.all())]
    for node in names:
        host = Host(node, provider=provider)
        host.run_smartstate_analysis()
        wait_for(is_host_analysis_finished, [host.name], delay=15,
                 timeout="10m", fail_func=toolbar.refresh)
        navigate_to(host, 'Details')
        role_name = summary_title().split()[1].translate(None, '()')
        role_name = 'Compute' if role_name == 'NovaCompute' else role_name
        try:
            role_assoc = host.get_detail('Relationships', 'Deployment Role')
        except NoSuchElementException:
            role_assoc = host.get_detail('Relationships', 'Cluster / Deployment Role')
        soft_assert(role_name in role_assoc, 'Deployment roles misconfigured')


def test_roles_name():
    navigate_to(DeploymentRoles, 'All')
    my_roles_quads = list(Quadicon.all())
    for quad in my_roles_quads:
        role_name = str(quad.name).split('-')[1]
        assert role_name in ROLES


def test_roles_summary(provider, soft_assert):
    err_ptrn = '{} are shown incorrectly'
    navigate_to(DeploymentRoles('', provider), 'AllForProvider')
    roles_names = [q.name for q in Quadicon.all()]

    for name in roles_names:
        dr = DeploymentRoles(name, provider)
        navigate_to(dr, 'DetailsFromProvider')

        for v in ('Nodes', 'Direct VMs', 'All VMs'):
            res = dr.get_detail('Relationships', v)
            soft_assert(res.isdigit(), err_ptrn.format(v))

        for v in ('Total CPUs', 'Total Node CPU Cores'):
            res = dr.get_detail('Totals for Nodes', v)
            soft_assert(res.isdigit() and int(res) > 0, err_ptrn.format(v))

        total_cpu = dr.get_detail('Totals for Nodes', 'Total CPU Resources')
        soft_assert('GHz' in total_cpu, err_ptrn.format('Total CPU Resources'))
        total_memory = dr.get_detail('Totals for Nodes', 'Total Memory')
        soft_assert('GB' in total_memory, err_ptrn.format('Total Memory'))

        for v in ('Total Configured Memory', 'Total Configured CPUs'):
            res = dr.get_detail('Totals for VMs', v)
            soft_assert(res, err_ptrn.format(v))


def test_role_delete(provider):
    navigate_to(DeploymentRoles, 'All')
    quads = list(Quadicon.all())
    assert quads > 0
    role_name = choice(quads).name
    dr = DeploymentRoles(role_name, provider)
    dr.delete()
    flash.assert_no_errors()
    navigate_to(dr, 'AllForProvider')
    names = [q.name for q in list(Quadicon.all())]
    assert role_name not in names
