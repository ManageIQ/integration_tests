from textwrap import dedent

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.dialog_import_export import DialogImportExport
from cfme.base.credential import Credential
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.provisioning import do_vm_provisioning
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log_validator import LogValidator


pytestmark = [test_requirements.automate]


@pytest.fixture(scope="module")
def new_users(appliance):
    """This fixture creates new users"""
    users = [appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric(start="user_").lower(),
        credential=Credential(principal=fauxfactory.gen_alphanumeric(start="uid"),
                              secret=fauxfactory.gen_alphanumeric(4)),
        email=fauxfactory.gen_email(),
        groups=appliance.collections.groups.instantiate(description="EvmGroup-super_administrator"),
        cost_center="Workload",
        value_assign="Database",
    ) for _ in range(2)]

    yield users
    for user in users:
        user = appliance.rest_api.collections.users.get(name=user.name)
        user.action.delete()


@pytest.fixture(scope='function')
def infra_validate_request(domain):
    # Take the 'ProvisionRequestApproval' class and copy it for own purpose.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Infrastructure"
    ).namespaces.instantiate(name="VM").namespaces.instantiate(
        name="Provisioning").namespaces.instantiate(name="StateMachines").classes.instantiate(
        name="ProvisionRequestApproval").methods.instantiate(
        name="validate_request").copy_to(domain.name)

    method = domain.namespaces.instantiate(
        name="Infrastructure"
    ).namespaces.instantiate(name="VM").namespaces.instantiate(
        name="Provisioning").namespaces.instantiate(name="StateMachines").classes.instantiate(
        name="ProvisionRequestApproval").methods.instantiate(name="validate_request")
    return method


@pytest.fixture(scope='function')
def service_validate_request(domain):
    # Take the 'ProvisionRequestApproval' class and copy it for own purpose.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Service"
    ).namespaces.instantiate(name="Provisioning").namespaces.instantiate(
        name="StateMachines").classes.instantiate(
        name="ServiceProvisionRequestApproval").methods.instantiate(
        name="validate_request").copy_to(domain.name)

    method = domain.namespaces.instantiate(
        name="Service"
    ).namespaces.instantiate(name="Provisioning").namespaces.instantiate(
        name="StateMachines").classes.instantiate(
        name="ServiceProvisionRequestApproval").methods.instantiate(
        name="validate_request")
    return method


@pytest.mark.tier(3)
@pytest.mark.provider([VMwareProvider], scope="module")
@pytest.mark.meta(automates=[1671563, 1720273, 1728706])
def test_user_requester_for_lifecycle_provision(request, appliance, provider, setup_provider,
                                                new_users, generic_catalog_item,
                                                infra_validate_request, service_validate_request,
                                                provisioning):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: high
        initialEstimate: 1/6h
        tags: automate

    Bugzilla:
         1671563
         1720273
         1728706
    """
    script = """
    user = $evm.root['user']
    $evm.log(:info, "This is the user: #{user.userid}")

    $evm.log("info", "Listing Root Object Attributes:")
    $evm.root.attributes.sort.each { |k, v| $evm.log("info", "\t#{k}: #{v}") }
    $evm.log("info", "===========================================")
    """
    infra_validate_request.update(updates={"script": script})
    service_validate_request.update(updates={"script": script})

    with new_users[0]:
        # Log in with first user and order service catalog
        result = LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[".*This is the user: {name}.*".format(
                name=new_users[0].credential.principal)],
        )
        result.start_monitoring()
        service_catalogs = ServiceCatalogs(
            appliance, catalog=generic_catalog_item.catalog, name=generic_catalog_item.name
        )
        provision_request = service_catalogs.order()
        provision_request.wait_for_request()
        assert result.validate(wait="60s")

    with new_users[1]:
        # Log in with second user and provision instance via lifecycle
        result = LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[".*This is the user: {name}.*".format(
                name=new_users[1].credential.principal)],
        )
        result.start_monitoring()
        prov_data = {
            "catalog": {'vm_name': random_vm_name(context='provision')},
            "environment": {'automatic_placement': True},
        }
        do_vm_provisioning(appliance,
                           template_name=provisioning["template"],
                           provider=provider,
                           vm_name=prov_data['catalog']['vm_name'], provisioning_data=prov_data,
                           wait=False, request=None)
        request_description = 'Provision from [{template}] to [{vm}{msg}]'.format(
            template=provisioning["template"], vm=prov_data['catalog']['vm_name'], msg='')
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        request.addfinalizer(provision_request.remove_request)
        assert result.validate(wait="60s")


@pytest.fixture(scope="module")
def setup_dynamic_dialog(appliance, custom_instance):
    # Create custom instance with ruby method
    code = dedent(
        """
        $evm.log(:info, "Hello World")
        """
    )
    instance = custom_instance(ruby_code=code)

    # Create dynamic dialog
    element_data = {
        "element_information": {
            "ele_label": fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            "ele_name": fauxfactory.gen_alphanumeric(15, start="ele_name_"),
            "ele_desc": fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            "dynamic_chkbox": True,
            "choose_type": "Text Box",
        },
        "options": {"entry_point": instance.tree_path},
    }

    service_dialog = appliance.collections.service_dialogs.create(
        label=fauxfactory.gen_alphanumeric(start="dialog_"), description="my dialog"
    )
    tab = service_dialog.tabs.create(
        tab_label=fauxfactory.gen_alphanumeric(start="tab_"), tab_desc="my tab desc"
    )
    box = tab.boxes.create(
        box_label=fauxfactory.gen_alphanumeric(start="box_"), box_desc="my box desc"
    )
    box.elements.create(element_data=[element_data])

    yield service_dialog
    service_dialog.delete_if_exists()


@pytest.mark.tier(2)
def test_automate_method_with_dialog(request, appliance, catalog, setup_dynamic_dialog):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/15h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
    """
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=fauxfactory.gen_alphanumeric(),
        description="my catalog", display_in=True, catalog=catalog,
        dialog=setup_dynamic_dialog.label
    )
    request.addfinalizer(catalog_item.delete_if_exists)
    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log", matched_patterns=[".*Hello World.*"]
    ).waiting(timeout=120):
        service_catalogs = ServiceCatalogs(
            appliance, catalog=catalog_item.catalog, name=catalog_item.name
        )
        provision_request = service_catalogs.order()
        provision_request.wait_for_request()
        request.addfinalizer(provision_request.remove_request)


@pytest.fixture(scope="function")
def copy_klass(domain):
    """This fixture copies ServiceProvision_Template which is required while selecting instance in
    catalog item"""
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Service"
    ).namespaces.instantiate(name="Provisioning").namespaces.instantiate(
        name="StateMachines"
    ).classes.instantiate(
        name="ServiceProvision_Template"
    ).copy_to(
        domain.name
    )

    klass = (
        domain.namespaces.instantiate(name="Service")
        .namespaces.instantiate(name="Provisioning")
        .namespaces.instantiate(name="StateMachines")
        .classes.instantiate(name="ServiceProvision_Template")
    )
    yield klass
    klass.delete_if_exists()


@pytest.fixture(scope="function")
def catalog_item_setup(request, copy_klass, domain, catalog, dialog):
    """
    This fixture is used to create custom instance pointing to method. Selecting this instance as
    provisioning entry point for generic catalog item.
    """
    # Script for setting service variable
    script1 = dedent(
        """
        $evm.set_service_var('service_var', "test value for service var")
        """
    )

    # Script for checking service variable
    script2 = dedent(
        """
        var = $evm.service_var_exists?('service_var') && $evm.get_service_var('service_var')
        $evm.log("info", "service var: service_var = #{var}")
        """
    )
    script = [script1, script2]

    var = fauxfactory.gen_alpha()
    copy_klass.schema.add_fields({'name': var, 'type': 'State'})

    cat_list = []
    for i in range(2):
        # Creating automate methods
        method = copy_klass.methods.create(name=fauxfactory.gen_alphanumeric(),
                                           display_name=fauxfactory.gen_alphanumeric(),
                                           location='inline',
                                           script=script[i]
                                           )

        # Creating automate instances
        instance = copy_klass.instances.create(
            name=fauxfactory.gen_alphanumeric(),
            display_name=fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            fields={var: {"value": f"METHOD::{method.name}"}}
        )

        # Making provisioning entry points to select while creating generic catalog items
        entry_point = (
            "Datastore",
            f"{domain.name}",
            "Service",
            "Provisioning",
            "StateMachines",
            f"{copy_klass.name}",
            f"{instance.display_name} ({instance.name})",
        )
        # Creating generic catalog items
        catalog_item = domain.appliance.collections.catalog_items.create(
            domain.appliance.collections.catalog_items.GENERIC,
            name=fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            display_in=True,
            catalog=catalog,
            dialog=dialog,
            provisioning_entry_point=entry_point
        )
        cat_list.append(catalog_item)
        request.addfinalizer(cat_list[i].delete_if_exists)
    yield catalog_item, cat_list


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1678136])
@pytest.mark.ignore_stream("5.10")
def test_passing_value_between_catalog_items(request, appliance, catalog_item_setup):
    """
    Bugzilla:
         1678136

    Polarion:
        assignee: nansari
        casecomponent: Automate
        caseimportance: high
        initialEstimate: 1/6h
        startsin: 5.11
        tags: automate
    """
    catalog_item, cat_list = catalog_item_setup

    # Creating catalog bundle of two catalog items
    catalog_bundle = appliance.collections.catalog_bundles.create(
        name=fauxfactory.gen_alphanumeric(),
        description="catalog_bundle",
        display_in=True,
        catalog=catalog_item.catalog,
        dialog=catalog_item.dialog,
        catalog_items=[cat_list[0].name, cat_list[1].name],
    )
    request.addfinalizer(catalog_bundle.delete_if_exists)

    with LogValidator("/var/www/miq/vmdb/log/automation.log",
                      matched_patterns=[
                          ".*service var:.*service_var = test value for service var.*"],
                      ).waiting(timeout=120):

        # Ordering service catalog bundle
        service_catalogs = ServiceCatalogs(
            appliance, catalog_bundle.catalog, catalog_bundle.name
        )
        service_catalogs.order()
        request_description = (
            f'Provisioning Service [{catalog_bundle.name}] from [{catalog_bundle.name}]'
        )
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        request.addfinalizer(provision_request.remove_request)
        assert provision_request.is_succeeded(method="ui")


@pytest.mark.manual
@pytest.mark.tier(2)
@pytest.mark.meta(coverage=[1748353])
def test_service_retire_automate():
    """
    Bugzilla:
        1748353

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Create email retirement method & add it to automate
            2. Provision service with a retirement date
            3. Reach retirement date
            4. See automation logs
        expectedResults:
            1.
            2.
            3.
            4. The retirement should not run multiple times at the same time
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1740796], blockers=[BZ(1740796, forced_streams=["5.10"])])
def test_import_dialog_file_without_selecting_file(appliance, dialog):
    """
    Bugzilla:
        1740796

    Polarion:
        assignee: nansari
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. "Automation-->Automate--> Customization-->Import/Export--> Click export without a
               service dialog selected.
            2. Exit this screen and edit a service dialog and save
        expectedResults:
            1. Flash message: "At least 1 item must be selected for export"
            2. Error flash message should not appear
    """
    import_export = DialogImportExport(appliance)
    view = navigate_to(import_export, "DialogImportExport")
    view.export.click()
    view.flash.assert_message("At least 1 item must be selected for export")
    dialog.update({'label': fauxfactory.gen_alphanumeric()})


@pytest.fixture(scope="module")
def new_user(appliance):
    """This fixture creates new user which has permissions to perform operation on Vm"""
    user = appliance.collections.users.create(
        name=f"user_{fauxfactory.gen_alphanumeric().lower()}",
        credential=Credential(principal=f'uid{fauxfactory.gen_alphanumeric(4)}',
                              secret=fauxfactory.gen_alphanumeric(4)),
        email=fauxfactory.gen_email(),
        groups=appliance.collections.groups.instantiate(description="EvmGroup-vm_user"),
        cost_center="Workload",
        value_assign="Database",
    )
    yield user
    user = appliance.rest_api.collections.users.get(name=user.name)
    user.action.delete()


@pytest.mark.tier(2)
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1747159])
@pytest.mark.provider([VMwareProvider], scope='function', selector=ONE)
def test_retire_vm_now(setup_provider, full_template_vm, new_user):
    """
    Bugzilla:
        1747159

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup:
            1. Add infrastructure provider
            2. Provision VM
            3. Create new user with group EvmGroup-vm_user
        testSteps:
            1. Select 'Retire this vm' from the UI to retire the VM
            2. Check evm.logs
        expectedResults:
            1. VM should be retired
            2. No errors in evm logs
    """
    with new_user:
        with LogValidator("/var/www/miq/vmdb/log/evm.log",
                          failure_patterns=[".*ERROR.*"]).waiting(timeout=720):
            full_template_vm.retire()
            assert full_template_vm.wait_for_vm_state_change(desired_state="retired", timeout=720,
                                                             from_details=True)
