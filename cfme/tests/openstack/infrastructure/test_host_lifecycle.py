import pytest
from utils import testgen
from cfme.web_ui import Quadicon, toolbar as tb
from cfme.infrastructure.host import Host
from cfme.web_ui import InfoBlock
from cfme.fixtures import pytest_selenium as sel
from utils.wait import wait_for


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_manageable(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    tb.select('Configuration', 'Set Node to Manageable', invokes_alert=True)
    sel.handle_alert()
    result = host.get_detail('Openstack Hardware', 'Provision State')
    provider.refresh()

    if not result == "Manageable":
        wait_for(lambda: result,  delay=15, timeout="10m",
                 fail_func=lambda: tb.select('Reload'))
    return result


def test_host_available(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    tb.select('Configuration', 'Provide Nodes', invokes_alert=True)
    sel.handle_alert()
    result = host.get_detail('Openstack Hardware', 'Provision State')
    provider.refresh()
    
    if not result == "available":
        wait_for(lambda: result,  delay=15, timeout="10m",
                 fail_func=lambda: tb.select('Reload'))
    return result


def test_host_introspection(provider):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    tb.select('Configuration', 'Introspect Nodes', invokes_alert=True)
    sel.handle_alert()
    result = host.get_detail('Openstack Hardware', 'Introspected')
    provider.refresh()

    if not result == "true":
        wait_for(lambda: result,  delay=15, timeout="10m",
                 fail_func=lambda: tb.select('Reload'))
    return result


def test_host_registration(provider, reg_file):
    provider.load_details()
    sel.click(InfoBlock.element("Relationships", "Nodes"))
    my_quads = list(Quadicon.all())
    quad = my_quads[0]
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    # need a json file input to add here
    pass



