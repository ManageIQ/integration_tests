# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.control.explorer import alert_profiles
from cfme.fixtures.automate import DatastoreImport
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.service_catalogs.ui import OrderServiceCatalogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
    test_requirements.ansible,
    pytest.mark.tier(3),
]


@pytest.fixture(scope="module")
def ansible_credential(appliance, ansible_repository, full_template_modscope):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=credentials[full_template_modscope["creds"]]["username"],
        password=credentials[full_template_modscope["creds"]]["password"]
    )
    yield credential
    credential.delete_if_exists()


@pytest.fixture
def management_event_class(appliance, namespace):
    appliance.collections.domains.instantiate(
        "ManageIQ").namespaces.instantiate(
        "System").namespaces.instantiate(
        "Event").namespaces.instantiate(
        "CustomEvent").classes.instantiate(
        name="Alert").copy_to(namespace.domain)
    return appliance.collections.domains.instantiate(
        namespace.domain.name).namespaces.instantiate(
        "System").namespaces.instantiate(
        "Event").namespaces.instantiate(
        "CustomEvent").classes.instantiate(name="Alert")


@pytest.fixture
def management_event_method(management_event_class, ansible_repository):
    return management_event_class.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )


@pytest.fixture
def management_event_instance(management_event_class, management_event_method):
    return management_event_class.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={"meth1": {"value": management_event_method.name}}
    )


@pytest.fixture(scope="module")
def custom_vm_button(appliance, ansible_catalog_item):
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=appliance.collections.button_groups.VM_INSTANCE)
    button = buttongroup.buttons.create(
        type="Ansible Playbook",
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
        playbook_cat_item=ansible_catalog_item.name)
    yield button
    button.delete_if_exists()
    buttongroup.delete_if_exists()


@pytest.fixture
def alert(appliance, management_event_instance):
    _alert = appliance.collections.alerts.create(
        "Trigger by Un-Tag Complete {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate="Nothing",
        driving_event="Company Tag: Un-Tag Complete",
        notification_frequency="1 Minute",
        mgmt_event=management_event_instance.name,
    )
    yield _alert
    _alert.delete_if_exists()


@pytest.fixture
def alert_profile(appliance, alert, full_template_vm_modscope):
    _alert_profile = appliance.collections.alert_profiles.create(
        alert_profiles.VMInstanceAlertProfile,
        "Alert profile for {}".format(full_template_vm_modscope.name),
        alerts=[alert]
    )
    _alert_profile.assign_to("The Enterprise")
    yield
    _alert_profile.delete_if_exists()


@pytest.mark.meta(automates=[1729999])
def test_automate_ansible_playbook_method_type_crud(appliance, ansible_repository, klass):
    """CRUD test for ansible playbook method.

    Bugzilla:
        1729999
        1740769

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/12h
    """
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
    method.delete()


def test_automate_ansible_playbook_method_type(request, appliance, ansible_repository, domain,
                                               namespace, klass):
    """Tests execution an ansible playbook via ansible playbook method using Simulation.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/4h
    """
    klass.schema.add_field(name="execute", type="Method", data_type="String")
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={"execute": {"value": method.name}})

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
        '[[ -f "/var/tmp/modified-release" ]] && rm -f "/var/tmp/modified-release"'))
    assert appliance.ssh_client.run_command('[ -f "/var/tmp/modified-release" ]').success


def test_ansible_playbook_button_crud(ansible_catalog_item, appliance, request):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
    """
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


def test_embedded_ansible_custom_button_localhost(full_template_vm_modscope, custom_vm_button,
        appliance, ansible_service_request, ansible_service, ansible_catalog_item):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Localhost"
    view = navigate_to(full_template_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill("CFME Default Credential")
    order_dialog_view.submit_button.click()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == "localhost"
    assert view.provisioning.results.get_text_of("Status") == "successful"


def test_embedded_ansible_custom_button_target_machine(full_template_vm_modscope, custom_vm_button,
        ansible_credential, appliance, ansible_service_request, ansible_service):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Target Machine"
    view = navigate_to(full_template_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill(ansible_credential.name)
    order_dialog_view.submit_button.click()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == full_template_vm_modscope.ip_address
    assert view.provisioning.results.get_text_of("Status") == "successful"


def test_embedded_ansible_custom_button_specific_hosts(full_template_vm_modscope, custom_vm_button,
        ansible_credential, appliance, ansible_service_request, ansible_service):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Specific Hosts"
        custom_vm_button.hosts = full_template_vm_modscope.ip_address
    view = navigate_to(full_template_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill(ansible_credential.name)
    order_dialog_view.submit_button.click()
    wait_for(ansible_service_request.exists, num_sec=600)
    ansible_service_request.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == full_template_vm_modscope.ip_address
    assert view.provisioning.results.get_text_of("Status") == "successful"


@test_requirements.alert
def test_alert_run_ansible_playbook(full_template_vm_modscope, alert_profile, request, appliance):
    """Tests execution of an ansible playbook method by triggering a management event from an
    alert.

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/6h
    """
    added_tag = full_template_vm_modscope.add_tag()
    full_template_vm_modscope.remove_tag(added_tag)
    request.addfinalizer(lambda: appliance.ssh_client.run_command(
        '[[ -f "/var/tmp/modified-release" ]] && rm -f "/var/tmp/modified-release"'))
    try:
        wait_for(
            lambda: appliance.ssh_client.run_command('[ -f "/var/tmp/modified-release" ]').success,
            timeout=60)
    except TimedOutError:
        pytest.fail("Ansible playbook method hasn't been executed.")


@pytest.fixture(scope='module')
def set_repo(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        name="test_retry_playbooks",
        url="https://github.com/billfitzgerald0120/ansible_playbooks",
        description=fauxfactory.gen_alpha()
    )
    view = navigate_to(repository, "Details")
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=view.toolbar.refresh.click
    )
    yield repository
    repository.delete_if_exists()


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1625047])
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1625047.zip", "bz_1625047", None)],
    ids=['retry_playbook']
)
def test_embed_tower_playbook_with_retry_method(request, set_repo, appliance, import_datastore,
                                                import_data, catalog, dialog):
    """
    Bugzilla:
        1625047

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        testSteps:
            1. Enable Embedded Ansible
            2. Add repo - https://github.com/billfitzgerald0120/ansible_playbooks
            3. Import Ansible_StateMachine_Set_Retry
            4. Enable domain
            5. Create Catalog using set_retry_4_times playbook.
            6. Add a dummy dialog
            7. Add a catalog
            8. Add a new Catalog item (Generic Type)
            9. Order service
        expectedResults:
            1. Check Embedded Ansible Role is started.
            2. Check repo is added.
            3.
            4.
            5. Verify in the Catalog playbook set_retry_4_times is used.
            6.
            7.
            8.
            9. Check automation.log to make sure the playbook retried 3 times and then ended OK.
    """
    ansible_catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        display_in_catalog=True, catalog=f"My Company/{catalog}",
        provisioning={
            "repository": set_repo.name,
            "playbook": "set_retry_4_times.yml",
            "machine_credential": "CFME Default Credential",
            "use_exisiting": True,
            "provisioning_dialog_id": dialog.label
        }
    )

    ansible_service_catalog = ServiceCatalogs(appliance, catalog, ansible_catalog_item.name)
    service_request = ansible_service_catalog.order()
    service_request.wait_for_request(num_sec=300, delay=20)
    request_descr = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    service_id = appliance.rest_api.collections.service_requests.get(description=request_descr)

    @request.addfinalizer
    def _finalize():
        service = MyService(appliance, ansible_catalog_item.name)
        if service_request.exists():
            service_request.wait_for_request()
            appliance.rest_api.collections.service_requests.action.delete(id=service_id.id)

        if service.exists:
            service.delete()
