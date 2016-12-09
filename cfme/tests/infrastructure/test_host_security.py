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


def get_integer_value(x):
    return int(x.split(' ')[0])


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_security(provider, soft_assert):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    assert len(my_quads) > 0
    for quad in my_quads:
        host = Host(name=quad.name)
        host.run_smartstate_analysis()
        wait_for(lambda: is_host_analysis_finished(host.name), delay=15,
                 timeout="10m", fail_func=lambda: toolbar.select('Reload'))

        soft_assert(get_integer_value(
                host.get_detail("Security", "Users")) > 0,
                    "Nodes number of users is 0")
        soft_assert(get_integer_value(
                host.get_detail("Security", "Groups")) > 0,
                    "Nodes number of groups is 0")
        """
        @rrasouli - No patches test yet
                soft_assert(get_integer_value(
                host.get_detail("Security", "Patches")) > 0,
                    "Nodes number of patches is 0")
        """
        """
        @rrasouli - No Firewall Rules test yet
                soft_assert(get_integer_value(
                host.get_detail("Security", "Firewall Rules")) > 0,
                    "Nodes number of Firewall rules is 0")
        """
        """
        @rrasouli - No SSH Root test yet
                soft_assert(
                host.get_detail("Security", "SSH Root").lower() == 'yes',
                    "Nodes number of Firewall rules is 0")
        """

