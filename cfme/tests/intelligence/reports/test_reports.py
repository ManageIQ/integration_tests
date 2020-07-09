import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.fixtures.cli import provider_app_crud
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.intelligence.reports.reports import ReportDetailsView
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.rest.gen_data import groups as _groups
from cfme.rest.gen_data import users as _users
from cfme.rest.gen_data import vm as _vm
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.ftp import FTPException
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.rest import assert_response
from cfme.utils.update import update


pytestmark = [test_requirements.report, pytest.mark.tier(3), pytest.mark.sauce]

PROPERTY_MAPPING = {
    "cpu": "Allocated Virtual CPUs",
    "memory": "Allocated Memory in GB",
    "storage": "Allocated Storage in GB",
    "template": "Allocated Number of Templates",
    "vm": "Allocated Number of Virtual Machines",
}

# ========================================== Fixtures =============================================


@pytest.fixture(scope="function")
def set_and_get_tenant_quota(appliance):
    root_tenant = appliance.collections.tenants.get_root_tenant()

    view = navigate_to(root_tenant, "ManageQuotas")
    reset_data = view.form.read()

    tenant_quota_data = {
        "cpu_cb": True,
        "cpu": "10",
        "memory_cb": True,
        "memory": "50.0",
        "storage_cb": True,
        "storage": "150.0",
        "template_cb": True,
        "template": "5",
        "vm_cb": True,
        "vm": "15",
    }

    root_tenant.set_quota(**tenant_quota_data)

    data = dict()
    for key, value in PROPERTY_MAPPING.items():
        suffix = "GB" if "GB" in value else "Count"
        data[value] = f"{tenant_quota_data[key]} {suffix}"

    yield data

    root_tenant.set_quota(**reset_data)


@pytest.fixture(scope="function")
def tenant_report(appliance):
    tenant_report = appliance.collections.reports.instantiate(
        type="Tenants", subtype="Tenant Quotas", menu_name="Tenant Quotas"
    ).queue(wait_for_finish=True)

    yield tenant_report

    tenant_report.delete()


@pytest.fixture(scope="module")
def get_report(appliance, request):
    def _report(
        file_name, menu_name, preserve_owner=False, overwrite=False, custom_appliance=appliance
    ):
        appliance = custom_appliance
        collection = appliance.collections.reports

        # download the report from server
        fs = FTPClientWrapper(cfme_data.ftpserver.entities.reports)
        file_path = fs.download(file_name)

        # import the report
        collection.import_report(file_path, preserve_owner=preserve_owner, overwrite=overwrite)

        # instantiate report and return it
        report = collection.instantiate(
            type="My Company (All Groups)", subtype="Custom", menu_name=menu_name
        )
        request.addfinalizer(report.delete_if_exists)
        return report

    return _report


@pytest.fixture
def vm(appliance, provider, request):
    return _vm(request, provider, appliance)


@pytest.fixture
def create_custom_tag(appliance):
    # cannot create a category with uppercase in the name
    category_name = fauxfactory.gen_alphanumeric().lower()
    category = appliance.rest_api.collections.categories.action.create(
        {"name": f"{category_name}", "description": f"description_{category_name}"}
    )[0]
    assert_response(appliance)

    tag = appliance.rest_api.collections.tags.action.create(
        {
            "name": f"{category_name}_entry",
            "description": f"{category_name}_entry_description",
            "category": {"href": category.href},
        }
    )[0]
    assert_response(appliance)

    yield category_name

    tag.action.delete()
    category.action.delete()


@pytest.fixture(scope="function")
def rbac_api(appliance, request):
    user, user_data = _users(request, appliance, password="smartvm", group="EvmGroup-user")
    return appliance.new_rest_api_instance(
        entry_point=appliance.rest_api._entry_point, auth=(user[0].userid, user_data[0]["password"])
    )


@pytest.fixture
def restore_db(temp_appliance_preconfig, file_name):
    try:
        db_file = FTPClientWrapper(cfme_data.ftpserver.entities.databases).get_file(file_name)
    except FTPException:
        pytest.skip("Failed to fetch the file from FTP server.")

    db_path = f"/tmp/{db_file.name}"

    # Download the customer db on appliance
    result = temp_appliance_preconfig.ssh_client.run_command(
        f"curl -o {db_path} ftp://{db_file.link}"
    )
    if not result.success:
        pytest.fail("Failed to download the file to the appliance.")

    def _check_file_size(file_path, expected_size):
        return temp_appliance_preconfig.ssh_client.run_command(
            f"stat {file_path} | grep {expected_size}"
        ).success

    # assert the whole database was downloaded to make sure we do not test with broken database
    if not _check_file_size(db_path, db_file.filesize):
        pytest.skip("File downloaded to the appliance, but it looks broken.")

    is_major = True if temp_appliance_preconfig.version > "5.11" else False
    temp_appliance_preconfig.db.restore_database(db_path, is_major=is_major)


@pytest.fixture
def create_po_user_and_group(request, appliance):
    """This fixture creates custom user with tenant attached"""
    group = _groups(
        request,
        appliance,
        appliance.rest_api.collections.roles.get(name="EvmRole-super_administrator"),
        description="Preserve Owner Report Group",
    )
    _users(request, appliance, group=group.description, userid="pouser")


@pytest.fixture
def setup_vm(configure_fleecing, appliance, provider):
    vm = appliance.collections.infra_vms.instantiate(
        name=random_vm_name(context="report", max_length=20),
        provider=provider,
        template_name="env-rhel7-20-percent-full-disk-pvala-tpl",
    )
    vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    vm.smartstate_scan(wait_for_task_result=True)
    yield vm

    vm.cleanup_on_provider()


@pytest.fixture
def edit_service_name(service_vm):
    service, vm = service_vm
    new_name = f"vm-test_{service.name}"
    with update(service):
        service.name = new_name
    return service, vm


@pytest.fixture
def timezone(appliance):
    tz, visual_tz = "IST", "(GMT+05:30) Kolkata"
    current_timezone = appliance.user.my_settings.visual.timezone
    appliance.user.my_settings.visual.timezone = visual_tz
    yield tz
    appliance.user.my_settings.visual.timezone = current_timezone


@pytest.fixture
def setup_replicated_multiple_appliances_with_providers(
    temp_appliance_unconfig_funcscope, replicated_appliances
):
    second_remote_appliance = temp_appliance_unconfig_funcscope
    remote_appliance, global_appliance = replicated_appliances
    logger.info("Starting appliance replication configuration.")
    second_remote_appliance.configure(region=89, key_address=remote_appliance.hostname)
    second_remote_appliance.set_pglogical_replication(replication_type=":remote")
    global_appliance.add_pglogical_replication_subscription(second_remote_appliance.hostname)
    logger.info("Finished appliance replication configuration.")

    second_remote_appliance.browser_steal = True

    vmware_provider = provider_app_crud(VMwareProvider, remote_appliance)
    rhev_provider = provider_app_crud(RHEVMProvider, second_remote_appliance)

    vmware_provider.setup()
    rhev_provider.setup()

    return vmware_provider, rhev_provider, global_appliance


@pytest.fixture(params=["new-report", "existing-report"])
def saved_report(request, setup_replicated_multiple_appliances_with_providers, get_report):
    # here `appliance` is the global appliance
    appliance = setup_replicated_multiple_appliances_with_providers[-1]
    if request.param == "existing-report":
        report = appliance.collections.reports.instantiate(
            type="Configuration Management", subtype="Providers", menu_name="Providers Summary"
        )
    else:
        report = get_report(
            file_name="test_reports_in_global_region.yaml",
            menu_name="Custom Providers Summary Report",
            custom_appliance=appliance,
        )
    return report.queue(wait_for_finish=True)


# =========================================== Tests ===============================================


@pytest.mark.tier(1)
def test_non_admin_user_reports_access_rest(appliance, rbac_api):
    """ This test checks if a non-admin user with proper privileges can access all reports via API.

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/12h
        tags: report
        setup:
            1. Create a user with privilege to access reports and REST.
            2. Instantiate a MiqApi instance with the user.
        testSteps:
            1. Access all reports with the new user with the help of newly instantiated API.
        expectedResults:
            1. User should be able to access all reports.
    """
    report_data = rbac_api.collections.reports.all
    assert_response(appliance)
    assert len(report_data)


@pytest.mark.tier(1)
def test_reports_custom_tags(appliance, request, create_custom_tag):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/3h
        setup:
            1. Add custom tags to appliance using black console
                i. ssh to appliance, vmdb; rails c
                ii. cat = Classification.create_category!(
                    name: "rocat1", description: "read_only cat 1", read_only: true)
                iii. cat.add_entry(name: "roent1", description: "read_only entry 1")
        testSteps:
            1. Create a new report with the newly created custom tag/category.
        expectedResults:
            1. Report must be created successfully.
    """
    category_name = create_custom_tag
    report_data = {
        "menu_name": f"Custom Category Report {category_name}",
        "title": f"Custom Category Report Title {category_name}",
        "base_report_on": "Availability Zones",
        "report_fields": [
            f"Cloud Manager.My Company Tags : description_{category_name}",
            f"VMs.My Company Tags : description_{category_name}",
        ],
    }
    report = appliance.collections.reports.create(**report_data)
    request.addfinalizer(report.delete)
    assert report.exists


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize(
    "based_on",
    [
        ("Floating IPs", ["Address", "Status", "Cloud Manager : Name"]),
        ("Cloud Tenants", ["Name", "My Company Tags : Owner", "My Company Tags : Cost Center"]),
    ],
    ids=["floating_ips", "cloud_tenants"],
)
@pytest.mark.meta(automates=[1546927, 1504155])
def test_new_report_fields(appliance, based_on, request):
    """
    This test case tests report creation with new fields and values.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/3h
        startsin: 5.11
        testSteps:
            1. Create a report with the parametrized tags.
        expectedResults:
            1. Report should be created successfully.

    Bugzilla:
        1546927
        1504155
    """
    data = {
        "menu_name": "testing report",
        "title": "Testing report",
        "base_report_on": based_on[0],
        "report_fields": based_on[1],
    }
    report = appliance.collections.reports.create(**data)
    request.addfinalizer(report.delete_if_exists)
    assert report.exists


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1565171, 1519809])
def test_report_edit_secondary_display_filter(soft_assert, get_report):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/6h
        setup:
            1. Create/Copy a report with secondary (display) filter.
        testSteps:
            1. Edit the secondary filter and test if the report was updated.
        expectedResults:
            1. Secondary filter must be editable and it must be updated.

    Bugzilla:
        1565171
        1519809
    """
    report = get_report("filter_report.yaml", "test_filter_report")
    report.update(
        {
            "filter": {
                "primary_filter": (
                    "fill_find("
                    "field=VM and Instance.Guest Applications : Name, skey=STARTS WITH, "
                    "value=env, check=Check Count, ckey= = , cvalue=1"
                    ");select_first_expression;click_or;fill_find("
                    "field=VM and Instance.Guest Applications : Name, skey=STARTS WITH, "
                    "value=kernel, check=Check Count, ckey= = , cvalue=1)"
                ),
                "secondary_filter": (
                    "fill_field(EVM Custom Attributes : Name, INCLUDES, A);"
                    " select_first_expression;click_or;fill_field"
                    "(EVM Custom Attributes : Region Description, INCLUDES, E)"
                ),
            }
        }
    )

    view = report.create_view(ReportDetailsView, wait="10s")

    primary_filter = (
        '( FIND VM and Instance.Guest Applications : Name STARTS WITH "env" CHECK COUNT = 1'
        ' OR FIND VM and Instance.Guest Applications : Name STARTS WITH "kernel" CHECK COUNT = 1 )'
    )
    secondary_filter = (
        '( VM and Instance.EVM Custom Attributes : Name INCLUDES "A"'
        ' OR VM and Instance.EVM Custom Attributes : Region Description INCLUDES "E" )'
    )
    soft_assert(
        view.report_info.primary_filter.read() == primary_filter, "Primary Filter did not match."
    )
    soft_assert(
        view.report_info.secondary_filter.read() == secondary_filter,
        "Secondary Filter did not match.",
    )


@pytest.mark.tier(1)
@pytest.mark.meta(server_roles="+notifier", automates=[1677839])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
def test_send_text_custom_report_with_long_condition(
    setup_provider, smtp_test, request, get_report
):
    """
    Bugzilla:
        1677839
        1693727

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Create a report containing 1 or 2 columns
                and add a report filter with a long condition.(Refer BZ for more detail)
            2. Create a schedule for the report and check send_txt.
        testSteps:
            1. Queue the schedule and monitor evm log.
        expectedResults:
            1. There should be no error in the log and report must be sent successfully.
    """
    report = get_report("long_condition_report.yaml", "test_long_condition_report")
    data = {
        "timer": {"hour": "12", "minute": "10"},
        "email": {"to_emails": "test@example.com"},
        "email_options": {"send_if_empty": True, "send_txt": True},
    }
    schedule = report.create_schedule(**data)
    request.addfinalizer(schedule.delete_if_exists)

    # prepare LogValidator
    log = LogValidator("/var/www/miq/vmdb/log/evm.log", failure_patterns=[".*negative argument.*"])

    log.start_monitoring()
    schedule.queue()

    # assert that the mail was sent
    assert len(smtp_test.wait_for_emails(wait=200, to_address=data["email"]["to_emails"])) == 1
    # assert that the pattern was not found in the logs
    assert log.validate(), "Found error message in the logs."


@pytest.mark.tier(3)
def test_queue_tenant_quota_reports(set_and_get_tenant_quota, tenant_report):
    """This test case sets the tenant quota, generates a 'Tenant Quota' report
        and compares both the data.

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/10h
        tags: report
        setup:
            1. Set tenant quota
            2. Create the report
        testSteps:
            1. Compare the 'total quota' data in the reports and the quota that was set initially.
        expectedResults:
            1. Both the data must be same.
    """
    report_data = dict()
    for row in tenant_report.data.rows:
        if row["Quota Name"] in list(PROPERTY_MAPPING.values()):
            report_data[row["Quota Name"]] = row["Total Quota"]
    assert report_data == set_and_get_tenant_quota


@pytest.mark.tier(3)
def test_report_fullscreen_enabled(request, tenant_report, set_and_get_tenant_quota, soft_assert):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/12h
        tags: report
        setup:
            1. Navigate to Cloud > Intel > Reports > All Reports
        testSteps:
            1. Select a report that would generate an empty report on queueing.
            Queue it, navigate to it's `Details` page, click on Configuration and
            check the `Show Fullscreen Report` option.
            2. Select a report that would generate a populated report on queueing.
            Queue it, navigate to it's `Details` page, click on Configuration and
            check the `Show Fullscreen Report` option.
        expectedResults:
            1. `Show Fullscreen Report` option is Disabled.
            2. `Show Fullscreen Report` option is Enabled.
    """
    empty_report = tenant_report
    view = navigate_to(empty_report, "Details", use_resetter=False)
    assert not view.configuration.item_enabled("Show full screen Report")

    non_empty_report = tenant_report.parent.parent.queue(wait_for_finish=True)
    request.addfinalizer(non_empty_report.delete)

    view = navigate_to(non_empty_report, "Details", use_resetter=False)
    assert view.configuration.item_enabled("Show full screen Report")


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1504010])
@pytest.mark.provider(
    [InfraProvider, CloudProvider], selector=ONE_PER_CATEGORY, required_flags=["provision"]
)
def test_reports_online_vms(appliance, setup_provider, provider, request, vm):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
        testSteps:
            1. Add a provider.
            2. Power off a VM.
            3. Queue report (Operations > Virtual Machines > Online VMs (Powered On)).
            4. See if the powered off VM is present in the queued report.
        expectedResults:
            1.
            2.
            3.
            4. VM must not be present in the report data.

    Bugzilla:
        1504010
    """
    subject_vm = appliance.provider_based_collection(provider).instantiate(
        name=vm, provider=provider
    )
    assert subject_vm.rest_api_entity.exists

    # power off the VM
    subject_vm.rest_api_entity.action.stop()
    assert_response(appliance)

    # wait until VM's power state changes
    assert subject_vm.wait_for_power_state_change_rest("off")

    # queue the report
    saved_report = appliance.collections.reports.instantiate(
        type="Operations", subtype="Virtual Machines", menu_name="Online VMs (Powered On)"
    ).queue(wait_for_finish=True)
    request.addfinalizer(saved_report.delete_if_exists)

    view = navigate_to(saved_report, "Details")
    assert vm not in [row.vm_name.text for row in view.table.rows()]


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1678150])
def test_reports_filter_content(set_and_get_tenant_quota, tenant_report):
    """
    Bugzilla:
        1678150
        1741588

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/3h
        startsin: 5.11
        setup:
            1. Go to Cloud Intel -> Reports -> All Reports
            2. Select a report and queue it, make sure it's not empty.
        testSteps:
            1. Add a filter.
            2. Traverse through all the rows and check if the content is filtered.
        expectedResults:
            1.
            2. Content must be filtered.
    """
    search_term = "in GB"
    table = tenant_report.filter_report_content(field="Quota Name", search_term=search_term)
    expected = ["Allocated Memory in GB", "Allocated Storage in GB"]
    got = [row["Quota Name"].text for row in table.rows()]
    assert sorted(expected) == sorted(got)


@test_requirements.filtering
@pytest.mark.meta(automates=[1696412])
def test_reports_filter_expression_editor_disk_size(appliance, request, get_report):
    """
    Bugzilla:
        1696412

    Polarion:
        assignee: anikifor
        casecomponent: Reporting
        initialEstimate: 1/10h
    """
    report_name = "test_filter_report"
    report = get_report("filter_report.yaml", report_name)
    report.update(
        {
            "filter": {
                "primary_filter": ("fill_field(VM and Instance : Allocated Disk Storage, > , 1)")
            },
            "title": report_name,
        }
    )

    generated_report = appliance.collections.reports.instantiate(
        type="My Company (All Groups)", subtype="Custom", menu_name=report_name
    ).queue(wait_for_finish=True)
    request.addfinalizer(report.delete_if_exists)
    assert generated_report.exists


@pytest.mark.long_running
@pytest.mark.customer_scenario
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1725142])
@pytest.mark.parametrize("file_name", ["test_migration_db_510.backup"], ids=["customer_db"])
def test_reports_service_unavailable(temp_appliance_preconfig, file_name, restore_db):
    """
    Bugzilla:
        1725142
        1737123

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
        setup:
            1. Load customer database on the appliance.
        testSteps:
            1. Navigate to Reports.
            2. Navigate to `Details` page of the report with >31k rows.
        expectedResults:
            1. Reports must be accessible, there should be no 503 service unavailable error.
            2. Details page must be accessible.
    """
    appliance = temp_appliance_preconfig

    view = navigate_to(appliance.collections.reports, "All")
    assert view.is_displayed

    saved_report = appliance.collections.reports.instantiate(
        type="Configuration Management", subtype="Hosts", menu_name="Host vLANs and vSwitches"
    ).saved_reports.instantiate("06/17/19 11:46:59 UTC", "06/17/19 11:44:57 UTC", False)
    assert saved_report.exists


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1678150])
def test_reports_sort_column(set_and_get_tenant_quota, tenant_report):
    """
    Bugzilla:
        1678150

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/3h
        startsin: 5.11
        testSteps:
            1. Go to Cloud Intel -> Reports -> All Reports
            2. Select a report and queue it, make sure it's not empty.
            4. Sort the targetted column in ascending order and note the order of the content.
            5. Sort the targetted column in descending order and note the order of the content.
            6. Compare the ascending order with the reverse of descending order.
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. The orders must be same.
    """

    column_name = "Quota Name"
    view = navigate_to(tenant_report, "Details")

    # sort in ascending order and note the order
    tenant_report.sort_column(field=column_name, order="asc")
    asc_list = [row[column_name].text for row in view.data_view.table.rows()]

    # sort in the descending order and note the order
    tenant_report.sort_column(field=column_name, order="desc")
    desc_list = [row[column_name].text for row in view.data_view.table.rows()]

    # assert the ascending list is reverse of descending list
    assert desc_list == asc_list[::-1]


@pytest.mark.customer_scenario
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1638533])
@pytest.mark.parametrize("preserve_owner", [True, False])
def test_import_report_preserve_owner(preserve_owner, create_po_user_and_group, get_report):
    """
    Bugzilla:
        1638533
        1693719

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/2h
        setup:
            1. Have a report with user and group values other than that of the admin
                and note the user and group values.
            2. Create a group and user as mentioned in the report yaml.
        testSteps:
            1. While importing the report, mark `Preserve Owner` with the parametrization values.
            2. Assert the user and group values are as expected.
                i. If `preserve_owner` is True
                ii. If `preserve_owner` is False
        expectedResults:
            1. Report imported successfully.
            2.
                i. Then expected values will be the original user and group
                ii. Then expected values will be user and group of the currently logged in user
    """
    user = "pouser" if preserve_owner else "admin"
    group = "Preserve Owner Report Group" if preserve_owner else "EvmGroup-super_administrator"
    report = get_report(
        "preserve_owner_report.yaml",
        "Testing report",
        preserve_owner=preserve_owner,
        overwrite=True,
    )
    view = navigate_to(report, "Details")

    assert view.report_info.user.text == user
    assert view.report_info.group.text == group


@pytest.mark.tier(1)
@pytest.mark.long_running
@pytest.mark.customer_scenario
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.meta(automates=[1686281], server_roles=["+smartstate", "+smartproxy"])
def test_vm_volume_free_space_less_than_20_percent(
    appliance, setup_provider, provider, setup_vm, soft_assert
):
    """
    Bugzilla:
        1686281
        1696420

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/3h
        setup:
            1. Create a VM with <=20% free volume space.
            2. Enable SSA role.
            3. Perform SSA on the newly created VM and a few other VMs.
        testSteps:
            1. Queue the report
                [Configuration Management, Virtual Machines, VMs with Volume Free Space <= 20%]
        expectedResults:
            1. Recently created VM must be present in the report.
    """
    saved_report = appliance.collections.reports.instantiate(
        menu_name="VMs with Volume Free Space <= 20%",
        type="Configuration Management",
        subtype="Virtual Machines",
    ).queue(wait_for_finish=True)
    view = navigate_to(saved_report, "Details")

    rows = [
        row["Volume Free Space Percent"].text.strip("%")
        for row in view.table.rows(name=setup_vm.name)
    ]

    # This will assert that not all the column["Volume Free Space Percent"] values are empty.
    assert any(rows)

    # This will assert that all the column values are <= 20
    assert all(
        [float(row) <= 20.0 for row in rows if row]
    ), "Volume Free Space Percent is greater than 20%"


@pytest.mark.tier(1)
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1521167])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
def test_reports_generate_custom_conditional_filter_report(
    setup_provider, get_report, edit_service_name, provider
):
    """
    Bugzilla:
        1521167

    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.8
        setup:
            1. Create or edit a service with one of the above naming conventions (vm-test, My-Test)
            2. Have at least one VM in the service so the reporting will parse it
            3. Create a report with a conditional filter in it, such as:
               conditions: !ruby/object:MiqExpression exp: and: - IS NOT NULL: field:
               Vm.service-name - IS NOT NULL: field: Vm-ems_cluster_name.
        testSteps:
            1. Queue the report.
        expectedResults:
            1. Report must be generated successfully.
    """
    service, vm = edit_service_name
    saved_report = get_report("vm_service_report", "VM Service").queue(wait_for_finish=True)
    view = navigate_to(saved_report, "Details")
    assert view.table.row(name__contains=vm.name)["Service Name"].text == service.name


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1743579], blockers=[BZ(1743579, forced_streams=["5.11", "5.10"])])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize("create_vm", ["small_template"], indirect=True, ids=[""])
def test_created_on_time_report_field(create_vm, get_report):
    """
    Bugzilla:
        1743579
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
        setup:
            1. Add a provider and provision a VM
        testSteps:
            1. Create a report based on 'VMs and Instances' with [Created on Time, Name] field.
        expectedResults:
            1. `Created on Time` field column must not be empty for the recently created VM.
    """
    report = get_report("vm_created_on_time_report.yaml", "VM Created on Time").queue(
        wait_for_finish=True
    )
    view = navigate_to(report, "Details")
    row = view.table.row(name=create_vm.name)
    # TODO BZ(1743579): assert with VM's created_on_time once the BZ is fixed.
    assert row.created_on_time.text != ""


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.meta(automates=[1599849])
def test_reports_timezone(setup_provider, timezone, get_report):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/10h
        startsin: 5.11
        setup:
            1. Navigate to My Settings and change the timezone.
            2. Create a report with the date created field
            3. Run report
        testSteps:
            1. Check the timezone in the report.
        expectedResults:
            1. Timezone must be same as set in My Settings.
    Bugzilla:
        1599849
    """
    report = get_report("vm_created_on_time_report.yaml", "VM Created on Time").queue(
        wait_for_finish=True
    )
    view = navigate_to(report, "Details")
    boot_time = [
        timezone in row.boot_time.text for row in view.table.rows() if row.boot_time.text != ""
    ]
    assert all(boot_time)


@pytest.mark.long_running
@test_requirements.multi_region
@pytest.mark.tier(2)
@pytest.mark.parametrize("context", [ViaREST, ViaUI])
def test_reports_in_global_region(
    context, saved_report, setup_replicated_multiple_appliances_with_providers
):
    """
    This test case tests report creation and rendering from global region
    based on data from remote regions.

    Polarion:
        assignee: tpapaioa
        casecomponent: Reporting
        caseimportance: critical
        initialEstimate: 1/2h
        testSteps:
            1. Set up Multi-Region deployment with 2 remote region appliances
            2. Add provider to each remote appliance
            3. Create and render report in global region. report should use data from both providers
            4. Use one of existing reports using data from added providers
        expectedResults:
            1.
            2.
            3. Report should be created and rendered successfully and show expected data.
            4. Report should be rendered successfully and show expected data.

    """
    vmware_provider, rhev_provider, _ = setup_replicated_multiple_appliances_with_providers

    # get list of provider names from the report generated in global appliance
    if context == ViaUI:
        view = navigate_to(saved_report, "Details")
        actual_data = [row["Name"].text for row in view.table.rows()]
    else:
        # since the appliance is temporary and only one saved report is present, we can use indexing
        result = saved_report.report.rest_api_entity.results.all[0]
        actual_data = [data["name"] for data in result.result_set]

    assert all(provider in actual_data for provider in [vmware_provider.name, rhev_provider.name])
