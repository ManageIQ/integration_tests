# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.configure.configuration import server_roles_enabled, candu
from cfme.control import explorer
from cfme.exceptions import CFMEExceptionOccured
from cfme.web_ui import flash, jstimelines
from utils import ports, testgen
from utils.conf import credentials
from utils.log import logger
from utils.net import net_check
from utils.providers import existing_providers, get_crud
from utils.ssh import SSHClient
from utils.update import update
from utils.wait import wait_for
from cfme import test_requirements


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+automate", "+notifier"]),
    pytest.mark.usefixtures("provider", "full_template"),
    pytest.mark.tier(3),
    test_requirements.alert
]

CANDU_PROVIDER_TYPES = {"virtualcenter"}  # TODO: rhevm


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if args["provider"].type in {"scvmm"}:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def wait_for_alert(smtp, alert, delay=None, additional_checks=None):
    """DRY waiting function

    Args:
        smtp: smtp_test funcarg
        alert: Alert name
        delay: Optional delay to pass to wait_for
        additional_checks: Additional checks to perform on the mails. Keys are names of the mail
            sections, values the values to look for.
    """
    logger.info("Waiting for informative e-mail of alert %s to come", alert.description)
    additional_checks = additional_checks or {}

    def _mail_arrived():
        for mail in smtp.get_emails():
            if "Alert Triggered: {}".format(alert.description) in mail["subject"]:
                if not additional_checks:
                    return True
                else:
                    for key, value in additional_checks.iteritems():
                        if value in mail.get(key, ""):
                            return True
        return False
    wait_for(
        _mail_arrived,
        num_sec=delay,
        delay=5,
        message="wait for e-mail to come!"
    )


def setup_for_alerts(request, alerts, event=None, vm_name=None, provider=None):
    """This function takes alerts and sets up CFME for testing it. If event and further args are
    not specified, it won't create the actions and policy profiles.

    Args:
        request: py.test funcarg request
        alerts: Alert objects
        event: Event to hook on (VM Power On, ...)
        vm_name: VM name to use for policy filtering
        provider: funcarg provider
    """
    alert_profile = explorer.VMInstanceAlertProfile(
        "Alert profile for {}".format(vm_name),
        alerts
    )
    alert_profile.create()
    request.addfinalizer(alert_profile.delete)
    alert_profile.assign_to("The Enterprise")
    if event is not None:
        action = explorer.Action(
            "Evaluate Alerts for {}".format(vm_name),
            "Evaluate Alerts",
            alerts
        )
        action.create()
        request.addfinalizer(action.delete)
        policy = explorer.VMControlPolicy(
            "Evaluate Alerts policy for {}".format(vm_name),
            scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
        )
        policy.create()
        request.addfinalizer(policy.delete)
        policy_profile = explorer.PolicyProfile(
            "Policy profile for {}".format(vm_name), [policy]
        )
        policy_profile.create()
        request.addfinalizer(policy_profile.delete)
        policy.assign_actions_to_event(event, [action])
        provider.assign_policy_profiles(policy_profile.description)
        request.addfinalizer(lambda: provider.unassign_policy_profiles(policy_profile.description))


# TODO: When we get rest, just nuke all providers, and add our one, no need to target delete
@pytest.yield_fixture(scope="module")
def initialize_provider(provider, setup_provider_modscope):
    # Remove other providers
    for provider_key in existing_providers():
        if provider_key == provider.key:
            continue
        provider_to_delete = get_crud(provider_key)
        if provider_to_delete.exists:
            provider_to_delete.delete(cancel=False)
    # Take care of C&U settings
    if provider.type not in CANDU_PROVIDER_TYPES:
        yield provider
    else:
        try:
            with server_roles_enabled(
                    'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor'):
                candu.enable_all()
                yield provider
        finally:
            candu.disable_all()


@pytest.fixture(scope="function")
def vm_name(request, initialize_provider, full_template):
    name = "test_alerts_{}".format(fauxfactory.gen_alpha())

    @request.addfinalizer
    def _cleanup_vm():
        try:
            if initialize_provider.mgmt.does_vm_exist(name):
                initialize_provider.mgmt.delete_vm(name)
            initialize_provider.refresh_provider_relationships()
        except Exception as e:
            logger.exception(e)
    vm_obj = VM.factory(name, initialize_provider, template_name=full_template["name"])
    vm_obj.create_on_provider(allow_skip="default")
    initialize_provider.mgmt.start_vm(vm_obj.name)
    initialize_provider.mgmt.wait_vm_running(vm_obj.name)
    # In order to have seamless SSH connection
    vm_ip, _ = wait_for(
        lambda: initialize_provider.mgmt.current_ip_address(vm_obj.name),
        num_sec=300, delay=5, fail_condition={None}, message="wait for testing VM IP address.")
    wait_for(
        net_check, [ports.SSH, vm_ip], {"force": True},
        num_sec=300, delay=5, message="testing VM's SSH available")
    if not vm_obj.exists:
        initialize_provider.refresh_provider_relationships()
        vm_obj.wait_to_appear()
    if initialize_provider.type in CANDU_PROVIDER_TYPES:
        vm_obj.wait_candu_data_available(timeout=20 * 60)
    return name


@pytest.fixture(scope="function")
def ssh(provider, full_template, vm_name):
    return SSHClient(
        username=credentials[full_template['creds']]['username'],
        password=credentials[full_template['creds']]['password'],
        hostname=provider.mgmt.get_ip_address(vm_name))


@pytest.fixture(scope="function")
def vm_crud(provider, vm_name, full_template):
    return VM.factory(vm_name, provider, template_name=full_template["name"])


@pytest.mark.meta(server_roles=["+automate", "+notifier"], blockers=[1266547])
def test_alert_vm_turned_on_more_than_twice_in_past_15_minutes(
        vm_name, vm_crud, provider, request, smtp_test, register_event):
    """ Tests alerts for vm turned on more than twice in 15 minutes

    Metadata:
        test_flag: alerts, provision
    """
    alert = explorer.Alert("VM Power On > 2 in last 15 min")
    with update(alert):
        alert.emails = fauxfactory.gen_email()

    setup_for_alerts(request, [alert], "VM Power On", vm_name, provider)

    if not provider.mgmt.is_vm_stopped(vm_name):
        provider.mgmt.stop_vm(vm_name)
    provider.refresh_provider_relationships()
    register_event('VmOrTemplate', vm_name, ['request_vm_poweroff', 'vm_poweoff'])
    vm_crud.wait_for_vm_state_change(vm_crud.STATE_OFF)
    for i in range(5):
        vm_crud.power_control_from_cfme(option=vm_crud.POWER_ON, cancel=False)
        register_event('VmOrTemplate', vm_name, ['request_vm_start', 'vm_start'])
        wait_for(lambda: provider.mgmt.is_vm_running(vm_name), num_sec=300)
        vm_crud.wait_for_vm_state_change(vm_crud.STATE_ON)
        vm_crud.power_control_from_cfme(option=vm_crud.POWER_OFF, cancel=False)
        register_event('VmOrTemplate', vm_name, ['request_vm_poweroff', 'vm_poweroff'])
        wait_for(lambda: provider.mgmt.is_vm_stopped(vm_name), num_sec=300)
        vm_crud.wait_for_vm_state_change(vm_crud.STATE_OFF)

    wait_for_alert(smtp_test, alert, delay=16 * 60)


@pytest.mark.uncollectif(lambda provider: provider.type not in CANDU_PROVIDER_TYPES)
def test_alert_rtp(request, vm_name, smtp_test, provider):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    email = fauxfactory.gen_email()
    alert = explorer.Alert(
        "Trigger by CPU {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate=(
            "Real Time Performance",
            {
                "performance_field": "CPU - % Used",
                "performance_field_operator": ">",
                "performance_field_value": "0",
                "performance_trend": "Don't Care",
                "performance_time_threshold": "3 Minutes",
            }),
        notification_frequency="5 Minutes",
        emails=email,
    )
    alert.create()
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])
    wait_for_alert(smtp_test, alert, delay=30 * 60, additional_checks={
        "text": vm_name, "from_address": email})


@pytest.mark.uncollectif(lambda provider: provider.type not in CANDU_PROVIDER_TYPES)
def test_alert_timeline_cpu(request, vm_name, provider, ssh, vm_crud):
    """ Tests a custom alert that uses C&U data to trigger an alert. It will run a script that makes
    a CPU spike in the machine to trigger the threshold. The alert is displayed in the timelines.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    alert = explorer.Alert(
        "TL event by CPU {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate=(
            "Real Time Performance",
            {
                "performance_field": "CPU - % Used",
                "performance_field_operator": ">",
                "performance_field_value": "20",
                "performance_trend": "Don't Care",
                "performance_time_threshold": "2 Minutes",
            }),
        notification_frequency="5 Minutes",
        timeline_event=True,
    )
    alert.create()
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])
    # Generate a 100% CPU spike for 5 minutes, that should be noticed by CFME.
    ssh.cpu_spike(seconds=5 * 60, cpus=4)

    def _timeline_event_present():
        vm_crud.open_timelines()
        select = pytest.sel.Select("//select[@name='tl_fl_grp2']")  # TODO: Make a timelines module?
        pytest.sel.select(select, "Alarm/Status change/Errors")
        for event in jstimelines.events():
            info = event.block_info()
            if info.get("Event Type") != "EVMAlertEvent":
                continue
            if info.get("Event Source") != "MiqAlert":
                continue
            if info["Source VM"] == vm_name:
                return True
        return False

    wait_for(_timeline_event_present, num_sec=30 * 60, delay=15, message="timeline event present")


@pytest.mark.skipif(True, reason="SNMP hogs the tests.")
@pytest.mark.uncollectif(lambda provider: provider.type not in CANDU_PROVIDER_TYPES)
def test_alert_snmp(request, vm_name, smtp_test, provider, snmp_client):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available. It uses SNMP to catch the
    alerts. It uses SNMP v2.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    alert = explorer.Alert(
        "Trigger by CPU {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate=(
            "Real Time Performance",
            {
                "performance_field": "CPU - % Used",
                "performance_field_operator": ">",
                "performance_field_value": "0",
                "performance_trend": "Don't Care",
                "performance_time_threshold": "3 Minutes",
            }),
        notification_frequency="5 Minutes",
        snmp_trap={
            "hosts": "127.0.0.1",  # The client lives on the appliance due to network reasons
            "version": "v2",
            "id": "1",
            "traps": [
                ("1.2.3", "Integer", "1")]},
    )
    alert.create()
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])

    def _snmp_arrived():
        # TODO: More elaborate checking
        for trap in snmp_client.get_all():
            if trap["source_ip"] != "127.0.0.1":
                continue
            if trap["trap_version"] != 2:
                continue
            if trap["oid"] != "1.0":
                continue
            for var in trap["vars"]:
                if var["name"] == "1.2.3" and var["oid"] == "1.2.3" and var["value"] == "1":
                    return True
        else:
            return False

    wait_for(_snmp_arrived, num_sec=600, delay=15, message="SNMP trap arrived.")


@pytest.mark.meta(blockers=[1231889], automates=[1231889])
def test_vmware_alarm_selection_does_not_fail():
    """Test the bug that causes CFME UI to explode when VMware Alarm type is selected.

    Metadata:
        test_flag: alerts
    """
    alert = explorer.Alert(
        "Trigger by CPU {}".format(fauxfactory.gen_alpha(length=4)),
        active=True,
        based_on="VM and Instance",
        evaluate=("VMware Alarm", {}),
        notification_frequency="5 Minutes",
    )
    try:
        alert.create()
    except CFMEExceptionOccured as e:
        pytest.fail("The CFME has thrown an error: {}".format(str(e)))
    except Exception as e:
        flash.assert_message_contain("must be configured")
    else:
        pytest.fail("Creating this alert passed although it must fail.")
