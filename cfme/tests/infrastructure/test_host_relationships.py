
import pytest
from utils import testgen
from cfme.web_ui import Quadicon, toolbar
from cfme.infrastructure.host import Host
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel
from cfme.configure.tasks import is_host_analysis_finished
from utils.wait import wait_for


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = \
        testgen.infra_providers(metafunc, required_fields=["ssh_credentials"])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist,
                        scope="module")

ROLES = ['Compute', 'Controller', 'BlockStorage', 'ObjectStorage',
         'CephStorage']


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_vms(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        result = int(host.get_detail('Relationships', 'VMs'))
#       @rrasouli need to add comparison to total numbder of vms, currently
        #  greater than 0
        assert result > 0


def test_host_role(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    result = False
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(
                lambda: is_host_analysis_finished(host.name), delay=15,
                timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        host_role = host.get_detail(
                'Relationships', 'Deployment Role').split('-')[1]
        if host_role in ROLES:
            result = True
    assert result
