# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic_patternfly import Button as WButton

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.common.vm import VM
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
from cfme.services.myservice import MyService
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.update import update
from cfme.utils.wait import wait_for
from markers.env_markers.provider import ONE_PER_TYPE


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream", "5.8"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
    test_requirements.ansible
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.yield_fixture(scope="module")
def ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        name=fauxfactory.gen_alpha(),
        url="https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha())
    view = navigate_to(repository, "Details")
    if appliance.version < "5.9":
        refresh = view.browser.refresh
    else:
        refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=refresh
    )
    yield repository

    if repository.exists:
        repository.delete()


@pytest.yield_fixture(scope='module')
def domain(appliance):
    dc = appliance.collections.domains
    d = dc.create(
        name='test_{}'.format(fauxfactory.gen_alpha()),
        enabled=True)
    yield d
    d.delete()


@pytest.fixture(scope="module")
def namespace(domain):
    return domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )


@pytest.fixture(scope="module")
def klass(namespace):
    klass_ = namespace.classes.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    klass_.schema.add_field(name="execute", type="Method", data_type="String")
    return klass_


@pytest.fixture(scope="module")
def method(klass, ansible_repository):
    return klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )


@pytest.fixture(scope="module")
def instance(klass, method):
    return klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={"execute": {"value": method.name}})


@pytest.yield_fixture(scope="module")
def ansible_catalog_item(ansible_repository):
    cat_item = AnsiblePlaybookCatalogItem(
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        display_in_catalog=True,
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric(),
            "extra_vars": [("some_var", "some_value")]
        }
    )
    cat_item.create()
    yield cat_item

    if cat_item.exists:
        cat_item.delete()


@pytest.yield_fixture
def custom_vm_button(appliance, ansible_catalog_item):
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=appliance.collections.button_groups.VM_INSTANCE)
    button = buttongroup.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
        dialog=ansible_catalog_item.provisioning["provisioning_dialog_name"],
        system="Request",
        request="Order_Ansible_Playbook",
        attributes=[
            {"key": "hosts", "value": "localhost"},
            {"key": "service_template_name", "value": ansible_catalog_item.name}
        ]
    )
    yield button
    button.delete_if_exists()
    buttongroup.delete_if_exists()


@pytest.yield_fixture(scope="module")
def vmware_vm(full_template_modscope, provider):
    vm_obj = VM.factory(random_vm_name("ansible"), provider,
                        template_name=full_template_modscope.name)
    vm_obj.create_on_provider(allow_skip="default")
    provider.mgmt.start_vm(vm_obj.name)
    provider.mgmt.wait_vm_running(vm_obj.name)
    if not vm_obj.exists:
        provider.refresh_provider_relationships()
        vm_obj.wait_to_appear()
    yield vm_obj
    if provider.mgmt.does_vm_exist(vm_obj.name):
        provider.mgmt.delete_vm(vm_obj.name)
    provider.refresh_provider_relationships()


@pytest.yield_fixture
def service_request(appliance, ansible_catalog_item):
    request_desc = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request_ = appliance.collections.requests.instantiate(request_desc)
    yield service_request_

    if service_request_.exists:
        service_request_.remove_request()


@pytest.yield_fixture
def service(appliance, ansible_catalog_item):
    service_ = MyService(appliance, ansible_catalog_item.name)
    yield service_

    if service_.exists:
        service_.delete()


def test_automate_ansible_playbook_method_type_crud(appliance, ansible_repository, domain,
        namespace, klass):
    """CRUD test for ansible playbook method."""
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )
    with update(method):
        method.name = fauxfactory.gen_alphanumeric()
        method.playbook = "dump_all_variables.yml"
    method.delete()


def test_automate_ansible_playbook_method_type(request, appliance, domain, namespace, klass,
        instance, method):
    """Tests execution an ansible playbook via ansible playbook method using Simulation."""
    simulate(
        appliance=appliance,
        request="Call_Instance",
        attributes_values={
            "namespace": "{}/{}".format(domain.name, namespace.name),
            "class": klass.name,
            "instance": instance.name
        }
    )
    request.addfinalizer(lambda: appliance.ssh_client.run_command(
        "if [ -f \"/var/tmp/modified-release\" ]; then rm \"/var/tmp/modified-release\""))
    assert appliance.ssh_client.run_command("[ -f \"/var/tmp/modified-release\" ]").success


def test_ansible_playbook_button_crud(ansible_catalog_item, appliance, request):
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=appliance.collections.button_groups.VM_INSTANCE)
    request.addfinalizer(buttongroup.delete_if_exists)
    button = buttongroup.buttons.create(
        type='Ansible Playbook',
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        playbook_cat_item=ansible_catalog_item.name)
    request.addfinalizer(button.delete_if_exists)
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.text.text == button.text
    assert view.hover.text == button.hover
    edited_hover = "edited {}".format(fauxfactory.gen_alphanumeric())
    with update(button):
        button.hover = edited_hover
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.hover.text == edited_hover
    button.delete(cancel=True)
    assert button.exists
    button.delete()
    assert not button.exists


def test_custom_button_order_ansible_playbook_service(setup_provider, vmware_vm, custom_vm_button,
        service_request, service, appliance):
    view = navigate_to(vmware_vm, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    submit_button = WButton(appliance.browser.widgetastic, "Submit")
    submit_button.click()
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "localhost"
    assert view.provisioning.results.get_text_of("Status") == "successful"
