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


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_vm_name(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        name = host.name.split(' ')
        host_type = name[1]
        if host_type not in '(NovaCompute)':
            break
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))
        result = int(host.get_detail('Relationships', 'VMs'))
#       @rrasouli need to add comparison to VM name, currently
        #  greater name is has cirros in it, might fail with 2 computes
        assert result > 0
        sel.click(InfoBlock.element("Relationships", "VMs"))
        vm_quads = list(Quadicon.all())
        for vm_quad in vm_quads:
            assert vm_quad in "cirros"




