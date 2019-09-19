import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.intelligence.reports.reports import ReportDetailsView
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.rest.gen_data import users as _users
from cfme.rest.gen_data import vm as _vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.log_validator import LogValidator
from cfme.utils.rest import assert_response

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
        data[value] = "{data_value} {suffix}".format(
            data_value=tenant_quota_data[key], suffix=suffix
        )

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
    def _report(file_name, menu_name):
        collection = appliance.collections.reports

        # download the report from server
        fs = FTPClientWrapper(cfme_data.ftpserver.entities.reports)
        file_path = fs.download(file_name)

        # import the report
        collection.import_report(file_path)

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
        {
            "name": "{cat_name}".format(cat_name=category_name),
            "description": "description_{cat_name}".format(cat_name=category_name),
        }
    )[0]
    assert_response(appliance)

    tag = appliance.rest_api.collections.tags.action.create(
        {
            "name": "{cat_name}_entry".format(cat_name=category_name),
            "description": "{cat_name}_entry_description".format(
                cat_name=category_name
            ),
            "category": {"href": category.href},
        }
    )[0]
    assert_response(appliance)

    yield category_name

    tag.action.delete()
    category.action.delete()


@pytest.fixture(scope="function")
def rbac_api(appliance, request):
    user, user_data = _users(
        request, appliance, password="smartvm", group="EvmGroup-user"
    )
    return appliance.new_rest_api_instance(
        entry_point=appliance.rest_api._entry_point,
        auth=(user[0].userid, user_data[0]["password"]),
    )


@pytest.fixture
def restore_db(temp_appliance_preconfig, file_name):
    db_file = FTPClientWrapper(cfme_data.ftpserver.entities.databases).get_file(file_name)
    db_path = f"/tmp/{db_file.name}"

    # Download the customer db on appliance
    result = temp_appliance_preconfig.ssh_client.run_command(
        f"curl -o {db_path} ftp://{db_file.link}"
    )
    assert result.success

    def _check_file_size(file_path, expected_size):
        return temp_appliance_preconfig.ssh_client.run_command(
            f"stat {file_path} | grep {expected_size}"
        ).success

    # assert the whole database was downloaded to make sure we do not test with broken database
    assert _check_file_size(db_path, db_file.filesize)

    is_major = True if temp_appliance_preconfig.version > "5.11" else False
    temp_appliance_preconfig.db.restore_database(db_path, is_major=is_major)


# =========================================== Tests ===============================================


@pytest.mark.tier(1)
def test_non_admin_user_reports_access_rest(appliance, request, rbac_api):
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
        "menu_name": "Custom Category Report {}".format(category_name),
        "title": "Custom Category Report Title {}".format(category_name),
        "base_report_on": "Availability Zones",
        "report_fields": [
            "Cloud Manager.My Company Tags : description_{}".format(category_name),
            "VMs.My Company Tags : description_{}".format(category_name),
        ],
    }
    report = appliance.collections.reports.create(**report_data)
    request.addfinalizer(report.delete)
    assert report.exists


@pytest.mark.tier(0)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize(
    "based_on",
    [
        ("Floating IPs", ["Address", "Status", "Cloud Manager : Name"]),
        (
            "Cloud Tenants",
            ["Name", "My Company Tags : Owner", "My Company Tags : Cost Center"],
        ),
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
def test_report_edit_secondary_display_filter(
    appliance, request, soft_assert, get_report
):
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
        view.report_info.primary_filter.read() == primary_filter,
        "Primary Filter did not match.",
    )
    soft_assert(
        view.report_info.secondary_filter.read() == secondary_filter,
        "Secondary Filter did not match.",
    )


@pytest.mark.tier(1)
@pytest.mark.meta(server_roles="+notifier", automates=[1677839])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
def test_send_text_custom_report_with_long_condition(
    appliance, setup_provider, smtp_test, request, get_report
):
    """
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

    Bugzilla:
        1677839
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
    log = LogValidator(
        "/var/www/miq/vmdb/log/evm.log", failure_patterns=[".*negative argument.*"]
    )

    log.start_monitoring()
    schedule.queue()

    # assert that the mail was sent
    assert (
        len(smtp_test.wait_for_emails(wait=200, to_address=data["email"]["to_emails"]))
        == 1
    )
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
        type="Operations",
        subtype="Virtual Machines",
        menu_name="Online VMs (Powered On)",
    ).queue(wait_for_finish=True)
    request.addfinalizer(saved_report.delete_if_exists)

    view = navigate_to(saved_report, "Details")
    assert vm not in [row.vm_name.text for row in view.table.rows()]


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.uncollectif(
    lambda case_sensitive: not case_sensitive
    and BZ("1741588", forced_streams=["5.11"]).blocks,
    reason="Case Insensitive filtering is still a WIP"
)
@pytest.mark.parametrize(
    "case_sensitive", [True, False], ids=["case-sensitive", "case-insensitive"]
)
@pytest.mark.meta(automates=[1678150, 1741588])
def test_reports_filter_content(
    appliance, case_sensitive, set_and_get_tenant_quota, tenant_report
):
    """
    Bugzilla:
        1678150

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
    search_term = "in GB" if case_sensitive else "in gb"
    table = tenant_report.filter_report_content(
        field="Quota Name", search_term=search_term
    )
    expected = ["Allocated Memory in GB", "Allocated Storage in GB"]
    got = [row["Quota Name"].text for row in table.rows()]
    assert sorted(expected) == sorted(got)


@pytest.mark.long_running
@pytest.mark.customer_scenario
@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1725142])
@pytest.mark.parametrize("file_name", ["test_migration_db_510.backup"], ids=["customer_db"])
def test_reports_service_unavailable(temp_appliance_preconfig, file_name, restore_db):
    """
    Bugzilla:
        1725142
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
        type="Configuration Management",
        subtype="Hosts",
        menu_name="Host vLANs and vSwitches",
    ).saved_reports.instantiate("06/17/19 11:46:59 UTC", "06/17/19 11:44:57 UTC", False)
    assert saved_report.exists
