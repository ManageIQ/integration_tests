import pytest
from navmazing import NavigationDestinationNotFound
from utils import testgen
from cfme.web_ui import Quadicon, toolbar as tb
from cfme.infrastructure.host import Host
from cfme.fixtures import pytest_selenium as sel
from utils.appliance.implementations.ui import navigate_to
from utils.wait import wait_for


pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack-infra'],
                                         scope='module')


@pytest.mark.usefixtures("setup_provider_modscope")
def test_host_manageable(provider):
    try:
        navigate_to(provider, 'ProviderNodes')
    except NavigationDestinationNotFound:
        assert "Missing nodes in provider's details"
    my_quads = list(Quadicon.all())
    quad_dict = {i.name: i for i in my_quads}
    # TODO remove the quad name, retrieve it from mgmt system
    quad = quad_dict['c4f7a679-b895-44dd-9436-d6f469a07513']
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    tb.select('Configuration', 'Set Node to Manageable', invokes_alert=True)
    sel.handle_alert()
    result = host.get_host_provisioning_state(provider)
    if not result == "Manageable":
        wait_for(lambda: result, delay=15,
                 timeout="10m", fail_func=lambda: tb.select('Reload'))
    return result


def test_host_available(provider):
    my_quads = list(Quadicon.all())
    try:
        navigate_to(provider, 'ProviderNodes')
    except NavigationDestinationNotFound:
        assert "Missing nodes in provider's details"
    quad_dict = {i.name: i for i in my_quads}
    # TODO remove the quad name, retrieve it from mgmt system
    quad = quad_dict['c4f7a679-b895-44dd-9436-d6f469a07513']
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    tb.select('Configuration', 'Provide Nodes', invokes_alert=True)
    sel.handle_alert()
    result = host.get_host_provisioning_state(provider)
    if not result == "available":
        wait_for(lambda: result, delay=15,
                 timeout="10m", fail_func=lambda: tb.select('Reload'))
    return result


def test_host_introspection(provider):
    my_quads = list(Quadicon.all())
    try:
        navigate_to(provider, 'ProviderNodes')
    except NavigationDestinationNotFound:
        assert "Missing nodes in provider's details"
    quad_dict = {i.name: i for i in my_quads}
    # TODO remove the quad name, retrieve it from mgmt system
    quad = quad_dict['c4f7a679-b895-44dd-9436-d6f469a07513']
    host = Host(name=quad.name)
    sel.check(quad.checkbox())
    tb.select('Configuration', 'Introspect Nodes', invokes_alert=True)
    sel.handle_alert()
    result = host.get_detail('Openstack Hardware', 'Introspected')
    provider.refresh()

    if not result == "true":
        wait_for(lambda: result, delay=15,
                 timeout="10m", fail_func=lambda: tb.select('Reload'))
    return result


def test_host_registration(provider, file_path):
    try:
        navigate_to(provider, 'ProviderNodes')
    except NavigationDestinationNotFound:
        assert "Missing nodes in provider's details"

    provider.register(file_path)
    assert provider.node_exist()
