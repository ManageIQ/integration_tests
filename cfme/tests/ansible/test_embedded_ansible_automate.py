# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from widgetastic_patternfly import Button as WButton

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.control.explorer import alert_profiles
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs.ui import OrderServiceCatalogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError, wait_for
from cfme.markers.env_markers.provider import ONE_PER_TYPE


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream", "5.8"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
    test_requirements.ansible,
    pytest.mark.uncollectif(lambda appliance: appliance.version < "5.9" and appliance.is_pod,
                            reason="5.8 pod appliance doesn't support embedded ansible"),
    pytest.mark.tier(3),
    pytest.mark.meta(blockers=[BZ(1640533, forced_streams=["5.10"])])
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.server.settings.enable_server_roles("embedded_ansible")
    appliance.wait_for_embedded_ansible()
    yield
    appliance.server.settings.disable_server_roles("embedded_ansible")


@pytest.fixture(scope="module")
def ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    try:
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=cfme_data.ansible_links.playbook_repositories.embedded_ansible,
            description=fauxfactory.gen_alpha())
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
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


@pytest.fixture(scope="module")
def ansible_credential(appliance, ansible_repository, full_template_modscope):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=credentials[full_template_modscope["creds"]]["username"],
        password=credentials[full_template_modscope["creds"]]["password"]
    )
    yield credential
    if credential.exists:
        credential.delete()


@pytest.fixture(scope='module')
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


@pytest.fixture
def management_event_class(appliance, namespace):
    appliance.collections.domains\
        .instantiate("ManageIQ")\
        .namespaces.instantiate("System")\
        .namespaces.instantiate("Event")\
        .namespaces.instantiate("CustomEvent")\
        .classes.instantiate(name="Alert")\
        .copy_to(namespace.domain)
    return appliance.collections.domains\
        .instantiate(namespace.domain.name)\
        .namespaces.instantiate("System")\
        .namespaces.instantiate("Event")\
        .namespaces.instantiate("CustomEvent")\
        .classes.instantiate(name="Alert")


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
        fields={"meth1": {"value": management_event_method.name}})


@pytest.fixture(scope="module")
def ansible_catalog_item(appliance, ansible_repository):
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
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
    yield cat_item

    if cat_item.exists:
        cat_item.delete()


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
def service_request(appliance, ansible_catalog_item):
    request_desc = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request_ = appliance.collections.requests.instantiate(request_desc)
    yield service_request_
    if service_request_.exists():
        service_request_.remove_request()


@pytest.fixture
def service(appliance, ansible_catalog_item):
    service_ = MyService(appliance, ansible_catalog_item.name)
    yield service_

    if service_.exists:
        service_.delete()


@pytest.fixture
def alert(appliance, management_event_instance):
    alert = appliance.collections.alerts.create(
        "Trigger by Un-Tag Complete {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate="Nothing",
        driving_event="Company Tag: Un-Tag Complete",
        notification_frequency="1 Minute",
        mgmt_event=management_event_instance.name,
    )
    yield alert
    if alert.exists:
        alert.delete()


@pytest.fixture
def alert_profile(appliance, alert, full_template_vm_modscope):
    alert_profile = appliance.collections.alert_profiles.create(
        alert_profiles.VMInstanceAlertProfile,
        "Alert profile for {}".format(full_template_vm_modscope.name),
        alerts=[alert]
    )
    alert_profile.assign_to("The Enterprise")
    yield
    if alert_profile.exists:
        alert_profile.delete()


def test_automate_ansible_playbook_method_type_crud(appliance, ansible_repository, domain,
        namespace, klass):
    """CRUD test for ansible playbook method.

    Polarion:
        assignee: dmisharo
        casecomponent: ansible
        caseimportance: medium
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
        method.playbook = "dump_all_variables.yml"
    method.delete()


def test_automate_ansible_playbook_method_type(request, appliance, domain, namespace, klass,
        instance, method):
    """Tests execution an ansible playbook via ansible playbook method using Simulation.

    Polarion:
        assignee: dmisharo
        casecomponent: ansible
        caseimportance: medium
        initialEstimate: 1/4h
    """
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
        assignee: dmisharo
        casecomponent: ansible
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
        appliance, service_request, service, ansible_catalog_item):
    """
    Polarion:
        assignee: mmojzis
        initialEstimate: None
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Localhost"
    view = navigate_to(full_template_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill("CFME Default Credential")
    order_dialog_view.submit_button.click()
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == "localhost"
    assert view.provisioning.results.get_text_of("Status") == "successful"


def test_embedded_ansible_custom_button_target_machine(full_template_vm_modscope, custom_vm_button,
        ansible_credential, appliance, service_request, service):
    """
    Polarion:
        assignee: dmisharo
        initialEstimate: None
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Target Machine"
    view = navigate_to(full_template_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill(ansible_credential.name)
    order_dialog_view.submit_button.click()
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == full_template_vm_modscope.ip_address
    assert view.provisioning.results.get_text_of("Status") == "successful"


def test_embedded_ansible_custom_button_specific_hosts(full_template_vm_modscope, custom_vm_button,
        ansible_credential, appliance, service_request, service):
    """
    Polarion:
        assignee: dmisharo
        initialEstimate: None
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
    wait_for(service_request.exists, num_sec=600)
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == full_template_vm_modscope.ip_address
    assert view.provisioning.results.get_text_of("Status") == "successful"


def test_alert_run_ansible_playbook(full_template_vm_modscope, alert_profile, request, appliance):
    """Tests execution of an ansible playbook method by triggering a management event from an
    alert.

    Polarion:
        assignee: jdupuy
        casecomponent: control
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
