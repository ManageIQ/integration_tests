import os

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainAddView
from cfme.automate.explorer.instance import InstanceCopyView
from cfme.automate.explorer.klass import ClassCopyView
from cfme.automate.explorer.method import MethodCopyView
from cfme.automate.import_export import FileImportSelectorView
from cfme.automate.simulation import simulate
from cfme.base.credential import Credential
from cfme.exceptions import OptionNotAvailable
from cfme.fixtures.automate import DatastoreImport
from cfme.rest.gen_data import groups as _groups
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import users as _users
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.mark.sauce
@pytest.mark.tier(1)
@pytest.mark.parametrize('enabled', [True, False], ids=['enabled', 'disabled'])
def test_domain_crud(request, enabled, appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/30h
        tags: automate
    """
    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=enabled)
    request.addfinalizer(domain.delete_if_exists)
    assert domain.exists
    view = navigate_to(domain, 'Details')
    if enabled:
        assert 'Disabled' not in view.title.text
    else:
        assert 'Disabled' in view.title.text
    updated_description = fauxfactory.gen_alpha(20, start="editdescription_")
    with update(domain):
        domain.description = updated_description
    view = navigate_to(domain, 'Edit')
    assert view.description.value == updated_description
    assert domain.exists
    domain.delete(cancel=True)
    assert domain.exists
    domain.delete()
    assert not domain.exists


@pytest.mark.tier(1)
def test_domain_edit_enabled(domain, appliance, request):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        initialEstimate: 1/16h
        caseimportance: high
        tags: automate
    """
    assert domain.exists
    view = navigate_to(domain, 'Details')
    assert 'Disabled' not in view.title.text
    with update(domain):
        domain.enabled = False
    view = navigate_to(domain, 'Details')
    assert 'Disabled' in view.title.text

    @request.addfinalizer
    def _finalize():
        with update(domain):
            domain.enabled = True


@pytest.mark.tier(2)
def test_domain_lock_disabled(klass, request):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/16h
        tags: automate
    """
    schema_field = fauxfactory.gen_alphanumeric()
    # Disable automate domain
    with update(klass.namespace.domain):
        klass.namespace.domain.enabled = False

    # Adding schema for executing automate method
    klass.schema.add_fields({'name': schema_field, 'type': 'Method', 'data_type': 'String'})

    # Adding automate method
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline'
    )

    # Adding instance to call automate method
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={schema_field: {'value': method.name}}
    )

    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log",
        matched_patterns=[r".*ERROR.*"],
    )
    result.start_monitoring()

    # Executing automate method using simulation
    simulate(
        appliance=klass.appliance,
        attributes_values={
            "namespace": klass.namespace.name,
            "class": klass.name,
            "instance": instance.name,
        },
        message="create",
        request="Call_Instance",
        execute_methods=True,
    )
    assert result.validate(wait="60s")

    klass.namespace.domain.lock()
    view = navigate_to(klass.namespace.domain, 'Details')
    assert 'Disabled' in view.title.text
    assert 'Locked' in view.title.text

    # Need to unlock the domain to perform teardown on domain, namespace, class
    klass.namespace.domain.unlock()

    @request.addfinalizer
    def _finalizer():
        with update(klass.namespace.domain):
            klass.namespace.domain.enabled = True


@pytest.mark.tier(1)
def test_domain_delete_from_table(request, appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/30h
        tags: automate
    """
    generated = []
    for _ in range(3):
        domain = appliance.collections.domains.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha(),
            enabled=True)
        request.addfinalizer(domain.delete_if_exists)
        generated.append(domain)

    appliance.collections.domains.delete(*generated)
    for domain in generated:
        assert not domain.exists


@pytest.mark.tier(2)
def test_duplicate_domain_disallowed(domain, appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/60h
        tags: automate
    """
    assert domain.exists
    with pytest.raises(Exception, match="Name has already been taken"):
        appliance.collections.domains.create(
            name=domain.name,
            description=domain.description,
            enabled=domain.enabled)


@pytest.mark.tier(2)
@pytest.mark.polarion('RHCF3-11228')
def test_domain_cannot_delete_builtin(appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: critical
        caseposneg: negative
        initialEstimate: 1/16h
        tags: automate
    """
    manageiq_domain = appliance.collections.domains.instantiate(name='ManageIQ')
    details_view = navigate_to(manageiq_domain, 'Details')
    assert not details_view.configuration.is_displayed


@pytest.mark.tier(2)
@pytest.mark.polarion('RHCF3-11227')
def test_domain_cannot_edit_builtin(appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: critical
        caseposneg: negative
        initialEstimate: 1/16h
        tags: automate
    """
    manageiq_domain = appliance.collections.domains.instantiate(name='ManageIQ')
    details_view = navigate_to(manageiq_domain, 'Details')
    assert not details_view.configuration.is_displayed


@pytest.mark.tier(2)
def test_wrong_domain_name(request, appliance):
    """To test whether domain is creating with wrong name or not.
       wrong_domain: 'Dummy Domain' (This is invalid name of Domain because there is space
       in the name)

    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/60h
        tags: automate
    """
    wrong_domain = 'Dummy Domain'
    domain = appliance.collections.domains
    with pytest.raises(AssertionError):
        domain.create(name=wrong_domain)
    view = domain.create_view(DomainAddView)
    view.flash.assert_message('Name may contain only alphanumeric and _ . - $ characters')
    wrong_domain = domain.instantiate(name=wrong_domain)
    request.addfinalizer(wrong_domain.delete_if_exists)
    assert not wrong_domain.exists


@pytest.mark.tier(2)
def test_domain_lock_unlock(domain, appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        initialEstimate: 1/16h
        caseimportance: medium
        tags: automate
    """
    assert domain.exists
    ns1 = domain.namespaces.create(name='ns1')
    ns2 = ns1.namespaces.create(name='ns2')
    cls = ns2.classes.create(name='class1')
    cls.schema.add_field(name='myfield', type='Relationship')
    inst = cls.instances.create(name='inst')
    meth = cls.methods.create(name='meth', script='$evm')
    # Lock the domain
    domain.lock()
    details = navigate_to(ns1, 'Details')
    assert not details.configuration.is_displayed
    details = navigate_to(ns2, 'Details')
    assert not details.configuration.is_displayed
    # class
    details = navigate_to(cls, 'Details')
    assert not details.configuration.is_enabled
    details.schema.select()
    assert not details.configuration.is_displayed
    # instance
    details = navigate_to(inst, 'Details')
    assert not details.configuration.is_enabled
    # method
    details = navigate_to(meth, 'Details')
    assert not details.configuration.is_enabled
    # Unlock it
    domain.unlock()
    # Check that it is editable
    with update(ns1):
        ns1.name = 'UpdatedNs1'
    assert ns1.exists
    with update(ns2):
        ns2.name = 'UpdatedNs2'
    assert ns2.exists
    with update(cls):
        cls.name = 'UpdatedClass'
    assert cls.exists
    cls.schema.add_field(name='myfield2', type='Relationship')
    with update(inst):
        inst.name = 'UpdatedInstance'
    assert inst.exists
    with update(meth):
        meth.name = 'UpdatedMethod'
    assert meth.exists


@pytest.mark.tier(1)
def test_object_attribute_type_in_automate_schedule(appliance):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        initialEstimate: 1/15h
        startsin: 5.9
        tags: automate
        testSteps:
            1. Go to Configuration > settings > schedules
            2. Select 'Add a new schedule' from configuration drop down
            3. selecting 'Automation Tasks' under Action.
            4. Select a value from the drop down list of Object Attribute Type.
            5. Undo the selection by selecting "<Choose>" from the drop down.
        expectedResults:
            1.
            2.
            3.
            4. No pop-up window with Internal Server Error.
            5. No pop-up window with Internal Server Error.

    Bugzilla:
         1479570
         1686762
    """
    view = navigate_to(appliance.collections.system_schedules, 'Add')
    view.form.action_type.select_by_visible_text('Automation Tasks')
    all_options = view.form.object_type.all_options
    if len(all_options) < 2:
        # There should be more than one options available because <choose> is default option
        raise OptionNotAvailable("Options not available")
    for option in all_options:
        if not (BZ(1686762).blocks and option.text in ['Tenant', 'EVM Group']):
            view.form.object_type.select_by_visible_text(option.text)
            view.flash.assert_no_error()
            view.form.object_type.select_by_visible_text('<Choose>')
            view.flash.assert_no_error()


@pytest.mark.tier(3)
def test_copy_to_domain(domain):
    """This test case checks whether automate class, instance and method are successfully copying to
    domain.

    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/15h
        startsin: 5.9
        tags: automate
        setup:
            1. Create new custom domain
        testSteps:
            1. Go to Automation > Automate > Explorer
            2. Select any class, instance and method from ManageIQ domain
            3. Copy selected things one by one to new custom domain by selecting
               "Copy this Method/Instance/Class" from configuration toolbar
        expectedResults:
            1.
            2.
            3. Class, Instance and Method should be copied to new domain and assert message should
               appear after copying these things to new domain.

    Bugzilla:
        1500956
    """
    # Instantiating default domain - 'ManageIQ'
    miq = (
        domain.appliance.collections.domains.instantiate("ManageIQ")
        .namespaces.instantiate("System")
        .namespaces.instantiate("CommonMethods")
    )

    # Instantiating Class - 'MiqAe' from 'ManageIQ' domain
    original_klass = miq.classes.instantiate("MiqAe")

    # Copy this Class to custom domain
    original_klass.copy_to(domain=domain)
    klass = domain.browser.create_view(ClassCopyView)
    klass.flash.wait_displayed()
    klass.flash.assert_message("Copy selected Automate Class was saved")

    # Instantiating Instance - 'quota_source' from 'ManageIQ' domain
    original_instance = miq.classes.instantiate("QuotaMethods").instances.instantiate(
        "quota_source"
    )

    # Copy this instance to custom domain
    original_instance.copy_to(domain=domain)
    instance = domain.browser.create_view(InstanceCopyView)
    instance.flash.wait_displayed()
    instance.flash.assert_message("Copy selected Automate Instance was saved")

    # Instantiating Method - 'rejected' from 'ManageIQ' domain
    original_method = miq.classes.instantiate("QuotaStateMachine").methods.instantiate("rejected")

    # Copy this method to custom domain
    original_method.copy_to(domain=domain)
    method = domain.browser.create_view(MethodCopyView)
    method.flash.wait_displayed()
    method.flash.assert_message("Copy selected Automate Method was saved")


@pytest.fixture(scope="function")
def new_user(request, appliance):
    """This fixture creates custom user with tenant attached"""
    tenant = _tenants(request, appliance)
    role = appliance.rest_api.collections.roles.get(name="EvmRole-super_administrator")
    group = _groups(request, appliance, role, tenant=tenant)
    user, user_data = _users(request, appliance, group=group.description)
    yield appliance.collections.users.instantiate(
        name=user[0].name,
        credential=Credential(principal=user_data[0]["userid"], secret=user_data[0]["password"]),
    ), tenant


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1678122])
@pytest.mark.ignore_stream("5.10")
def test_tenant_attached_with_domain(request, new_user, domain):
    """
    Note: This RFE which has introduced extra column for tenant on domain all view

    Bugzilla:
        1678122

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.11
        casecomponent: Automate
        setup: Create new user
        testSteps:
            1. Log in with admin. Create automate domain and navigate to domains all page
            2. Log in with new user. Create automate domain and navigate to domains all page
        expectedResults:
            1. Automate domain should be assigned with tenant - 'My Company'
            2. Automate domain should be assigned with new user's tenant
    """
    # Domain created by admin user attached with root tenant "My Company"
    user, tenant = new_user
    view = navigate_to(domain.parent, "All")
    assert view.domains.row(name=domain.name)["Tenant"].text == "My Company"

    # Log in with new user
    with user:
        # Domain created by new user attached with new tenant assigned to this user
        new_domain = domain.appliance.collections.domains.create(
            name=fauxfactory.gen_alpha(), description=fauxfactory.gen_alpha(), enabled=True
        )
        request.addfinalizer(new_domain.delete_if_exists)
        for domain in view.domains.read():
            if domain['Name'] == new_domain.name:
                assert domain['Tenant'] == tenant.name
            else:
                assert domain['Tenant'] == "My Company"


@pytest.fixture(scope='module')
def user(appliance):
    """Creates new user with role which does not have permission of modifying automate domains"""
    product_features = [
        (['Everything', 'Automation', 'Automate', 'Explorer', 'Automate Domains', 'Modify'], False)
    ]
    role = appliance.collections.roles.create(name=fauxfactory.gen_alphanumeric(),
                                              product_features=product_features)

    group = appliance.collections.groups.create(
        description=fauxfactory.gen_alphanumeric(),
        role=role.name,
        tenant=appliance.collections.tenants.get_root_tenant().name
    )

    user = appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric().lower(),
        credential=Credential(
            principal=fauxfactory.gen_alphanumeric(4),
            secret=fauxfactory.gen_alphanumeric(4),
        ),
        email=fauxfactory.gen_email(),
        groups=group,
        cost_center="Workload",
        value_assign="Database",
    )
    yield user
    user.delete_if_exists()
    group.delete_if_exists()
    role.delete_if_exists()


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1365493])
def test_automate_restrict_domain_crud(user, custom_instance):
    """
    When you create a role that can only view automate domains, it can view automate domains but it
    cannot manipulate the domains themselves as well as can not CRUD on namespaces, classes,
    instances etc.

    Bugzilla:
        1365493

    Polarion:
        assignee: dgaikwad
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
    """
    instance = custom_instance(ruby_code=None)
    with user:
        view = navigate_to(instance, "Details")
        assert not view.configuration.is_displayed
        view = navigate_to(instance.klass, "Details")
        assert not view.configuration.is_displayed
        view = navigate_to(instance.klass.namespace, "Details")
        assert not view.configuration.is_displayed
        view = navigate_to(instance.klass.namespace.domain, "Details")
        assert not view.configuration.is_displayed


@pytest.mark.tier(2)
@pytest.mark.long_running
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1693362], blockers=[BZ(1693362)])
@pytest.mark.parametrize("file_name", ["test_migration_db_510.backup"])
def test_redhat_domain_sync_after_upgrade(temp_appliance_preconfig, file_name):
    """
    Bugzilla:
        1693362

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        testSteps:
            1. Either dump database of appliance with version X to appliance with version Y
               or upgrade the appliance
            2. grep 'domain version on disk differs from db version' /var/www/miq/vmdb/log/evm.log
            3. Check last_startup.txt file
        expectedResults:
            1.
            2. You should find this string in logs: RedHat domain version on disk differs from db
               version
            3. You should find this string in file: RedHat domain version on disk differs from db
               version
    """
    db_file = FTPClientWrapper(cfme_data.ftpserver.entities.databases).get_file(file_name)
    db_path = os.path.join("/tmp", db_file.name)

    # Download the customer db on appliance
    assert temp_appliance_preconfig.ssh_client.run_command(
        f"curl -o {db_path} ftp://{db_file.link}"
    ).success

    with LogValidator(
        "/var/www/miq/vmdb/log/evm.log",
        matched_patterns=[".*domain version on disk differs from db version.*",
                          ".*RedHat domain version on disk differs from db version.*",
                          ".*ManageIQ domain version on disk differs from db version.*"],
    ).waiting(timeout=1000):
        temp_appliance_preconfig.db.restore_database(
            db_path, is_major=bool(temp_appliance_preconfig.version > "5.11")
        )


@pytest.fixture
def custom_domain(custom_instance):
    """This fixture creates dastastore setup and updates the name and description of domain. So that
       the domain with same name can be imported successfully.
    """
    instance = custom_instance(ruby_code=None)
    # Domain name and description are updated because we are importing domain with same name via
    # import datastore file
    domain_info = "bz_1752875"
    instance.domain.update({"name": domain_info, "description": domain_info})
    domain = instance.appliance.collections.domains.instantiate(name=domain_info,
                                                                description=domain_info)
    domain.lock()
    yield domain
    domain.delete_if_exists()


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1752875])
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1752875.zip", "bz_1752875", None)],
    ids=["domain"],
)
def test_existing_domain_child_override(appliance, custom_domain, import_data):
    """
    PR:
        https://github.com/ManageIQ/manageiq-ui-classic/pull/4912

    Bugzilla:
        1752875

    Polarion:
        assignee: dgaikwad
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
        setup: First three steps are performed manually to have datastore zip file
            1. Create custom domain and copy class - "ManageIQ/System/Process"
            2. Lock this domain
            3. Navigate to Automation > automate > Import/export and click on "export all classes
               and instances to file"
            4. Go to custom domain and unlock it. Remove instance - "ManageIQ/System/Process/" and
               copy - "ManageIQ/System/Process/Request" (you can copy more classes or methods or
               instances) to custom domain and again lock the domain.
        testSteps:
            1. Navigate to Import/Export page and import the exported file
            2. Select "Select domain you wish to import from:" - "custom_domain" and check Toggle
               All/None
            3. Click on commit button.
            4. Then navigate to custom domain and unlock it
            5. Perform step 1, 2 and 3(In this case, domain will get imported)
            6. Go to custom domain
        expectedResults:
            1.
            2.
            3. You should see flash message: "Error: Selected domain is locked"
            4.
            5. Selected domain imported successfully
            6. You should see imported namespace, class, instance or method
    """
    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(import_data.file_name)

    # Import datastore file to appliance
    datastore = appliance.collections.automate_import_exports.instantiate(
        import_type="file", file_path=file_path
    )
    datastore.import_domain_from(import_data.from_domain, import_data.to_domain)
    view = appliance.browser.create_view(FileImportSelectorView)
    view.flash.assert_message("Error: Cannot import into a locked domain.")
    custom_domain.unlock()
    datastore.import_domain_from(import_data.from_domain, import_data.to_domain)
    view.flash.assert_no_error()
    view = navigate_to(custom_domain, 'Details')
    assert view.datastore.tree.has_path('Datastore', f'{custom_domain.name}', 'System', 'Process')
