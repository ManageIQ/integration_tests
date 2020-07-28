import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.import_export import FileImportSelectorView
from cfme.automate.simulation import simulate
from cfme.control.explorer import alert_profiles
from cfme.fixtures.automate import DatastoreImport
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.service_catalogs.ui import OrderServiceCatalogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.log_validator import LogValidator
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
        fauxfactory.gen_alpha(start="cred_"),
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
        name=fauxfactory.gen_alphanumeric(start="meth_"),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )


@pytest.fixture
def management_event_instance(management_event_class, management_event_method):
    return management_event_class.instances.create(
        name=fauxfactory.gen_alphanumeric(start="inst_"),
        description=fauxfactory.gen_alphanumeric(),
        fields={"meth1": {"value": management_event_method.name}}
    )


@pytest.fixture(scope="module")
def custom_vm_button(appliance, ansible_catalog_item):
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
        type=appliance.collections.button_groups.VM_INSTANCE)
    button = buttongroup.buttons.create(
        type="Ansible Playbook",
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
        playbook_cat_item=ansible_catalog_item.name)
    yield button
    button.delete_if_exists()
    buttongroup.delete_if_exists()


@pytest.fixture
def alert(appliance, management_event_instance):
    _alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(30, start="Trigger by Un-Tag Complete "),
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
def alert_profile(appliance, alert, create_vm_modscope):
    _alert_profile = appliance.collections.alert_profiles.create(
        alert_profiles.VMInstanceAlertProfile,
        f"Alert profile for {create_vm_modscope.name}",
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
        assignee: dgaikwad
        casecomponent: Automate
        initialEstimate: 1/12h
    """
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(start="meth_"),
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
        assignee: dgaikwad
        casecomponent: Automate
        initialEstimate: 1/4h
    """
    klass.schema.add_field(name="execute", type="Method", data_type="String")
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(start="meth_"),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(start="inst_"),
        description=fauxfactory.gen_alphanumeric(),
        fields={"execute": {"value": method.name}})

    simulate(
        appliance=appliance,
        request="Call_Instance",
        attributes_values={
            "namespace": f"{domain.name}/{namespace.name}",
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
        assignee: gtalreja
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
    """
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
        type=appliance.collections.button_groups.VM_INSTANCE)
    request.addfinalizer(buttongroup.delete_if_exists)
    button = buttongroup.buttons.create(
        type='Ansible Playbook',
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
        playbook_cat_item=ansible_catalog_item.name)
    request.addfinalizer(button.delete_if_exists)
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.text.text == button.text
    assert view.hover.text == button.hover
    edited_hover = fauxfactory.gen_alphanumeric(15, start="edited_")
    with update(button):
        button.hover = edited_hover
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.hover.text == edited_hover
    button.delete(cancel=True)
    assert button.exists
    button.delete()
    assert not button.exists


@pytest.mark.parametrize('create_vm_modscope', ['full_template'], indirect=True)
def test_embedded_ansible_custom_button_localhost(create_vm_modscope, custom_vm_button,
        appliance, ansible_service_request_funcscope,
        ansible_service_funcscope, ansible_catalog_item):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Localhost"
    view = navigate_to(create_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill("CFME Default Credential")
    order_dialog_view.submit_button.click()
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service_funcscope, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == "localhost"
    status = "successful" if appliance.version < "5.11" else "Finished"
    assert view.provisioning.results.get_text_of("Status") == status


@pytest.mark.parametrize('create_vm_modscope', ['full_template'], indirect=True)
def test_embedded_ansible_custom_button_target_machine(create_vm_modscope, custom_vm_button,
        ansible_credential, appliance, ansible_service_request_funcscope,
        ansible_service_funcscope):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Target Machine"
    view = navigate_to(create_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill(ansible_credential.name)
    order_dialog_view.submit_button.click()
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service_funcscope, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == create_vm_modscope.ip_address
    status = "successful" if appliance.version < "5.11" else "Finished"
    assert view.provisioning.results.get_text_of("Status") == status


@pytest.mark.parametrize('create_vm_modscope', ['full_template'], indirect=True)
def test_embedded_ansible_custom_button_specific_hosts(create_vm_modscope, custom_vm_button,
        ansible_credential, appliance, ansible_service_request_funcscope,
        ansible_service_funcscope):
    """
    Polarion:
        assignee: gtalreja
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    with update(custom_vm_button):
        custom_vm_button.inventory = "Specific Hosts"
        custom_vm_button.hosts = create_vm_modscope.ip_address
    view = navigate_to(create_vm_modscope, "Details")
    view.toolbar.custom_button(custom_vm_button.group.text).item_select(custom_vm_button.text)
    order_dialog_view = appliance.browser.create_view(OrderServiceCatalogView)
    order_dialog_view.submit_button.wait_displayed()
    order_dialog_view.fields("credential").fill(ansible_credential.name)
    order_dialog_view.submit_button.click()
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service_funcscope, "Details")
    hosts = view.provisioning.details.get_text_of("Hosts")
    assert hosts == create_vm_modscope.ip_address
    status = "successful" if appliance.version < "5.11" else "Finished"
    assert view.provisioning.results.get_text_of("Status") == status


@test_requirements.alert
@pytest.mark.parametrize('create_vm_modscope', ['full_template'], indirect=True)
def test_alert_run_ansible_playbook(create_vm_modscope, alert_profile, request, appliance):
    """Tests execution of an ansible playbook method by triggering a management event from an
    alert.

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/6h
    """
    added_tag = create_vm_modscope.add_tag()
    create_vm_modscope.remove_tag(added_tag)
    request.addfinalizer(lambda: appliance.ssh_client.run_command(
        '[[ -f "/var/tmp/modified-release" ]] && rm -f "/var/tmp/modified-release"'))
    try:
        wait_for(
            lambda: appliance.ssh_client.run_command('[ -f "/var/tmp/modified-release" ]').success,
            timeout=60)
    except TimedOutError:
        pytest.fail("Ansible playbook method hasn't been executed.")


@pytest.fixture(scope='module')
def setup_ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    # Repository name(test_playbooks_automate) is static because this is already in the datastore
    # imported. If we used(fauxfactory.gen_alpha()) here then datastore import will fail with no
    # ansible repository available.
    repository = repositories.create(
        name="test_playbooks_automate",
        url=cfme_data.ansible_links.playbook_repositories.embedded_ansible,
        description=fauxfactory.gen_alpha()
    )
    view = navigate_to(repository, "Details")
    wait_for(
        lambda: repository.status == "successful",
        timeout=60,
        fail_func=view.toolbar.refresh.click
    )
    yield repository
    repository.delete_if_exists()


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1678132, 1678135])
@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize(
    ("import_data", "instance"),
    ([DatastoreImport("bz_1678135.zip", "Ansible_State_Machine_for_Ansible_stats3",
                      None), "CatalogItemInitialization_jira23"],
     [DatastoreImport("bz_1678135.zip", "Ansible_State_Machine_for_Ansible_stats3",
                      None), "CatalogItemInitialization_jira24"]),
    ids=["method_to_playbook", "playbook_to_playbook"]
)
def test_variable_pass(request, appliance, setup_ansible_repository, import_datastore, import_data,
                       instance, dialog, catalog):
    """
    Bugzilla:
        1678132
        1678135

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        startsin: 5.11
        setup:
            1. Enable embedded ansible role
            2. Add Ansible repo called billy -
               https://github.com/ManageIQ/integration_tests_playbooks
            3. Copy Export zip (Ansible_State_Machine_for_Ansible_stats3.zip) to downloads
               directory(Zip file named - 'Automate domain' is attached with BZ(1678135))
            4. Go to Automation>Automate>Import/Export and import zip file
            5. Click on "Toggle All/None" and hit the submit button
            6. Go to Automation>Automate>Explorer and Enable the imported domain
            7. Make sure all the playbook methods have all the information (see if Repository,
               Playbook and Machine credentials have values), update if needed
            8. Import or create hello_world (simple ansible dialog with Machine credentials and
               hosts fields)
        testSteps:
            1. Create a Generic service using the hello_world dialog.
            1a. Select instance 'CatalogItemInitialization_jira23'(Note: This is the state machine
                which executes playbooks and inline method successively) then order service
            1b. Select instance 'CatalogItemInitialization_jira24'(Note: This is the state machine
                which executes playbooks successively) then order service
            2. Run "grep dump_vars2 automation.log" from log directory
        expectedResults:
            1. Generic service catalog item created
            2. For 1a scenario: Variables should be passed through successive playbooks and you
               should see logs like this(https://bugzilla.redhat.com/show_bug.cgi?id=1678132#c5)
               For 1b scenario: Variables should be passed through successive playbooks and you
               should see logs like this(https://bugzilla.redhat.com/show_bug.cgi?id=1678135#c13)
    """
    # Making provisioning entry points to select while creating generic catalog items
    entry_point = (
        "Datastore",
        f"{import_datastore.name}",
        "Service",
        "Provisioning",
        "StateMachines",
        "ServiceProvision_Template",
        f"{instance}",
    )

    # Creating generic catalog items
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
        description=fauxfactory.gen_alphanumeric(15, start="item_disc_"),
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        provisioning_entry_point=entry_point,
    )

    with LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[
            ".*if Fred is married to Wilma and Barney is married to Betty and Peebles and BamBam "
            "are the kids, then the tests work !!!.*"
        ],
    ).waiting(timeout=120):
        # Ordering service catalog bundle
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        service_catalogs.order()
        request_description = "Provisioning Service [{0}] from [{0}]".format(catalog_item.name)
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method="ui")
        request.addfinalizer(provision_request.remove_request)


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1677575])
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1677575.zip", "bz_1677575", None)],
    ids=["datastore"],
)
def test_import_domain_containing_playbook_method(request, appliance, setup_ansible_repository,
                                                  import_data):
    """This test case tests support of Export/Import of Domain with Ansible Method

    Bugzilla:
        1677575

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/8h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.11
        casecomponent: Automate
        tags: automate
        setup:
            1. Add playbook repository
            2. Create a new automate method with playbook type.
            3. Fill the required fields, for instance repository and playbook.
            4. Export this datastore.
            5. Playbook method fields are stored as a names instead of IDs. (this is not
               possible via automate need to check manually in method yaml)
        testSteps:
            1. Import the exported datastore and change name of playbook in method yaml to invalid
               playbook name(Note: These test steps needs to execute manually and then import
               datastore)
        expectedResults:
            1. Proper error should be displayed while importing datastore with invalid playbook
    """
    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(import_data.file_name)

    # Import datastore file to appliance
    datastore = appliance.collections.automate_import_exports.instantiate(
        import_type="file", file_path=file_path
    )
    domain = datastore.import_domain_from(import_data.from_domain, import_data.to_domain)
    request.addfinalizer(domain.delete_if_exists)
    view = appliance.browser.create_view(FileImportSelectorView)
    # setup_ansible_repository.name is ansible repository name already there in datastore yml which
    # we are going to import.
    error_msg = (
        f"Playbook 'invalid_1677575.yml' not found in repository '{setup_ansible_repository.name}'"
    )
    view.flash.assert_message(text=error_msg, partial=True)


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1734629, 1734630])
@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize(
    ("import_data", "instance"),
    ([DatastoreImport("bz_1734629.zip", "ansible_set_stat",
                      None), "CatalogItemInitialization_29"],
     [DatastoreImport("bz_1734629.zip", "ansible_set_stat",
                      None), "CatalogItemInitialization_30"]),
    ids=["object_update", "set_service_var"]
)
def test_automate_ansible_playbook_set_stats(request, appliance, setup_ansible_repository,
import_datastore, import_data, instance, dialog, catalog):
    """
    Bugzilla:
        1734629
        1734630

    Polarion:
        assignee: gtalreja
        initialEstimate: 1/4h
        caseimportance: high
        caseposneg: positive
        casecomponent: Automate
        startsin: 5.11
        setup:
            1. Enable EmbeddedAnsible server role
            2. Add Ansible repo "test_playbooks_automate"
            3. Go to Automation>Automate>Import/Export and import zip file (ansible_set_stats.zip)
            5. Click on "Toggle All/None" and hit the submit button
            6. Go to Automation>Automate>Explorer and Enable the imported domain
            7. Make sure all the playbook methods have all the information (see if Repository,
               Playbook and Machine credentials have values), update if needed
        testSteps:
            1. Create a Generic service catalog using with dialog.
            1a. Select instance 'CatalogItemInitialization_29' then order service
            1b. Select instance 'CatalogItemInitialization_30' then order service
            2. Check automation.log from log directory
        expectedResults:
            1. Generic service catalog item created
            2. For 1a scenario: Playbook should pass with updated status and [:config_info][:active]
               and you should get logs like (https://bugzilla.redhat.com/show_bug.cgi?id=1734629#c8)
               For 1b scenario: Playbook should pass, verify new value setting to service_var and
               should get logs like this(https://bugzilla.redhat.com/show_bug.cgi?id=1734630#c9)
    """
    entry_point = (
        "Datastore",
        f"{import_datastore.name}",
        "Service",
        "Provisioning",
        "StateMachines",
        "ServiceProvision_Template",
        f"{instance}",
    )
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(15, start="cat_item_"),
        description=fauxfactory.gen_alphanumeric(15, start="item_disc_"),
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        provisioning_entry_point=entry_point,
    )

    @request.addfinalizer
    def _finalize():
        if catalog.exists:
            catalog.delete()
            catalog_item.catalog = None
        catalog_item.delete_if_exists()
        dialog.delete_if_exists()

    if instance == "CatalogItemInitialization_29":
        map_pattern = [
            '.*status = "Warn".*',
            '.*"config_info"=>{"active"=>true}.*'
        ]
    elif instance == "CatalogItemInitialization_30":
        map_pattern = ['.*:service_vars=>{"ansible_stats_var1"=>"secret"}.*']

    with LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=map_pattern
    ).waiting(timeout=300):
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
        service_catalogs.order()
        req_description = f"Provisioning Service [{catalog_item.name}] from [{catalog_item.name}]"
        provision_request = appliance.collections.requests.instantiate(req_description)
        provision_request.wait_for_request(method="ui")
