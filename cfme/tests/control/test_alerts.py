from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.control.explorer import alert_profiles
from cfme.control.explorer import policies
from cfme.control.explorer.alert_profiles import AlertProfileDetailsView
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.tests.control import do_scan
from cfme.tests.control import wait_for_ssa_enabled
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.ssh import SSHClient
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pf1 = ProviderFilter(classes=[InfraProvider])
pf2 = ProviderFilter(classes=[SCVMMProvider, RHEVMProvider], inverted=True)


CANDU_PROVIDER_TYPES = [VMwareProvider]

# note: RHV provider is not supported for alerts via the Cloudforms support matrix
pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+automate", "+smartproxy", "+notifier"]),
    pytest.mark.provider(CANDU_PROVIDER_TYPES, scope="module"),
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.tier(3),
    test_requirements.alert
]


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
                    for key, value in additional_checks.items():
                        if value in mail.get(key, ""):
                            return True
        return False
    wait_for(
        _mail_arrived,
        num_sec=delay,
        delay=5,
        message="wait for e-mail to come!"
    )


@pytest.fixture
def setup_for_alerts(appliance):
    """fixture wrapping the function defined within, for delayed execution during the test

    Returns:
        unbound function object for calling during the test
    """
    def _setup_for_alerts(request, alerts_list, event=None, vm_name=None, provider=None):
        """This function takes alerts and sets up CFME for testing it. If event and further args are
        not specified, it won't create the actions and policy profiles.

        Args:
            request: py.test funcarg request
            alerts_list: list of alert objects
            event: Event to hook on (VM Power On, ...)
            vm_name: VM name to use for policy filtering
            provider: funcarg provider
        """
        alert_profile = appliance.collections.alert_profiles.create(
            alert_profiles.VMInstanceAlertProfile,
            "Alert profile for {}".format(vm_name),
            alerts=alerts_list
        )
        request.addfinalizer(alert_profile.delete)
        view = appliance.browser.create_view(AlertProfileDetailsView)
        if alert_profile.assign_to("The Enterprise"):
            # change made
            view.flash.assert_message(
                'Alert Profile "{}" assignments successfully saved'
                .format(alert_profile.description)
            )
        else:
            # no assignment change made
            view.flash.assert_message('Edit Alert Profile assignments cancelled by user')
        if event is not None:
            action = appliance.collections.actions.create(
                "Evaluate Alerts for {}".format(vm_name),
                "Evaluate Alerts",
                action_values={"alerts_to_evaluate": [str(alert) for alert in alerts_list]}
            )
            request.addfinalizer(action.delete)
            policy = appliance.collections.policies.create(
                policies.VMControlPolicy,
                "Evaluate Alerts policy for {}".format(vm_name),
                scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
            )
            request.addfinalizer(policy.delete)
            policy_profile = appliance.collections.policy_profiles.create(
                "Policy profile for {}".format(vm_name), policies=[policy]
            )
            request.addfinalizer(policy_profile.delete)
            policy.assign_actions_to_event(event, [action])
            provider.assign_policy_profiles(policy_profile.description)
            request.addfinalizer(
                lambda: provider.unassign_policy_profiles(policy_profile.description))
    return _setup_for_alerts


@pytest.fixture(scope="module")
def set_performance_capture_threshold(appliance):
    yaml_data = {"performance": {"capture_threshold_with_alerts": {"vm": "3.minutes"}}}
    appliance.update_advanced_settings(yaml_data)
    yield
    yaml_data = {"performance": {"capture_threshold_with_alerts": {"vm": "20.minutes"}}}
    appliance.update_advanced_settings(yaml_data)


@pytest.fixture(scope="module")
def setup_candu(appliance):
    candu = appliance.collections.candus
    candu.enable_all()
    appliance.server.settings.enable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    yield
    appliance.server.settings.disable_server_roles(
        'ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor')
    candu.disable_all()


@pytest.fixture(scope="function")
def wait_candu(create_vm):
    create_vm.wait_candu_data_available(timeout=20 * 60)


@pytest.fixture(scope="function")
def ssh(provider, full_template, create_vm):
    with SSHClient(
            username=credentials[full_template.creds]['username'],
            password=credentials[full_template.creds]['password'],
            hostname=create_vm.mgmt.ip) as ssh_client:
        yield ssh_client


@pytest.fixture(scope="module")
def setup_snmp(appliance):
    appliance.ssh_client.run_command("echo 'disableAuthorization yes' >> /etc/snmp/snmptrapd.conf")
    appliance.ssh_client.run_command("systemctl start snmptrapd.service")
    yield
    appliance.ssh_client.run_command("systemctl stop snmptrapd.service")
    appliance.ssh_client.run_command("sed -i '$ d' /etc/snmp/snmptrapd.conf")


@pytest.mark.rhv3
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
@pytest.mark.provider(gen_func=providers, filters=[pf1, pf2], scope="module")
def test_alert_vm_turned_on_more_than_twice_in_past_15_minutes(
    request, appliance, provider, create_vm, smtp_test, setup_for_alerts
):
    """ Tests alerts for vm turned on more than twice in 15 minutes

    Metadata:
        test_flag: alerts, provision

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/4h
    """
    vm = create_vm
    alert = appliance.collections.alerts.instantiate("VM Power On > 2 in last 15 min")
    with update(alert):
        alert.active = True
        alert.emails = fauxfactory.gen_email()
        if appliance.version >= "5.11.0.7":
            alert.severity = "Error"

    setup_for_alerts(request, [alert], "VM Power On", vm.name, provider)

    vm.mgmt.ensure_state(VmState.STOPPED)
    provider.refresh_provider_relationships()
    vm.wait_for_vm_state_change(vm.STATE_OFF)
    for i in range(5):
        vm.power_control_from_cfme(option=vm.POWER_ON, cancel=False)
        vm.mgmt.wait_for_state(VmState.RUNNING, timeout=300)
        vm.wait_for_vm_state_change(vm.STATE_ON)
        vm.power_control_from_cfme(option=vm.POWER_OFF, cancel=False)
        vm.mgmt.wait_for_state(VmState.STOPPED)
        vm.wait_for_vm_state_change(vm.STATE_OFF)

    wait_for_alert(smtp_test, alert, delay=16 * 60)


@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_alert_rtp(request, appliance, create_vm, smtp_test, provider,
        setup_candu, wait_candu, setup_for_alerts):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available.

    Metadata:
        test_flag: alerts, provision, metrics_collection

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/6h
    """
    email = fauxfactory.gen_email()
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(length=20, start="Trigger by CPU "),
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
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])
    wait_for_alert(smtp_test, alert, delay=30 * 60, additional_checks={
        "text": create_vm.name, "from_address": email})


@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_alert_timeline_cpu(request, appliance, create_vm,
        set_performance_capture_threshold, provider, ssh, setup_candu, wait_candu,
        setup_for_alerts):
    """ Tests a custom alert that uses C&U data to trigger an alert. It will run a script that makes
    a CPU spike in the machine to trigger the threshold. The alert is displayed in the timelines.

    Metadata:
        test_flag: alerts, provision, metrics_collection

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/6h
    """
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(length=20, start="TL event by CPU "),
        active=True,
        based_on="VM and Instance",
        evaluate=(
            "Real Time Performance",
            {
                "performance_field": "CPU - % Used",
                "performance_field_operator": ">=",
                "performance_field_value": "10",
                "performance_trend": "Don't Care",
                "performance_time_threshold": "2 Minutes",
            }),
        notification_frequency="1 Minute",
        timeline_event=True,
    )
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert], vm_name=create_vm.name)
    # Generate a 100% CPU spike for 15 minutes, that should be noticed by CFME.
    ssh.cpu_spike(seconds=60 * 15, cpus=2, ensure_user=True)
    timeline = create_vm.open_timelines()
    timeline.filter.fill({
        "event_category": "Alarm/Status Change/Errors",
        "time_range": "Weeks",
        "calendar": "{dt.month}/{dt.day}/{dt.year}".format(dt=datetime.now() + timedelta(days=1))
    })
    timeline.filter.apply.click()
    events = timeline.chart.get_events()
    for event in events:
        if alert.description in event.message:
            break
    else:
        pytest.fail("The event has not been found on the timeline. Event list: {}".format(events))


@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_alert_snmp(request, appliance, provider, setup_snmp, setup_candu, create_vm,
        wait_candu, setup_for_alerts):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available. It uses SNMP to catch the
    alerts. It uses SNMP v2.

    Metadata:
        test_flag: alerts, provision, metrics_collection

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/6h
    """
    match_string = fauxfactory.gen_alpha(length=8)
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(length=20, start="Trigger by CPU "),
        active=True,
        based_on="VM and Instance",
        evaluate=(
            "Real Time Performance",
            {
                "performance_field": "CPU - % Used",
                "performance_field_operator": ">=",
                "performance_field_value": "0",
                "performance_trend": "Don't Care",
                "performance_time_threshold": "3 Minutes",
            }),
        notification_frequency="1 Minute",
        snmp_trap={
            "hosts": "127.0.0.1",
            "version": "v2",
            "id": "info",
            "traps": [
                ("1.2.3", "OctetString", "{}".format(match_string))]},
    )
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])

    def _snmp_arrived():
        result = appliance.ssh_client.run_command(
            "journalctl --no-pager /usr/sbin/snmptrapd | grep {}".format(match_string))
        if result.failed:
            return False
        elif result.output:
            return True
        else:
            return False

    wait_for(_snmp_arrived, timeout="30m", delay=60, message="SNMP trap arrived.")


@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_alert_hardware_reconfigured(request, appliance, configure_fleecing, smtp_test,
        create_vm, setup_for_alerts):
    """Tests alert based on "Hardware Reconfigured" evaluation.

    According https://bugzilla.redhat.com/show_bug.cgi?id=1396544 Hardware Reconfigured alerts
    require drift history. So here are the steps for triggering hardware reconfigured alerts based
    on CPU Count:
        1. Run VM smart state analysis.
        2. Change CPU count.
        3. Run VM smart state analysis again.
        4. Run VM reconfigure again.
    Then the alert for CPU count change should be triggered. It is either CPU increased or decreased
    depending on what has been done in your step 2, not the result of step 4. Step 4 is just to
    trigger the event.

    Bugzilla:
        1396544
        1730805

    Metadata:
        test_flag: alerts, provision

    Polarion:
        assignee: jdupuy
        casecomponent: Control
        initialEstimate: 1/4h
    """
    vm = create_vm
    email = fauxfactory.gen_email()
    service_request_desc = ("VM Reconfigure for: {0} - Processor Sockets: {1}, "
        "Processor Cores Per Socket: 1, Total Processors: {1}")
    alert = appliance.collections.alerts.create(
        fauxfactory.gen_alpha(length=36, start="Trigger by hardware reconfigured "),
        active=True,
        based_on="VM and Instance",
        evaluate=(
            "Hardware Reconfigured",
            {
                "hardware_attribute": "Number of CPU Cores",
                "operator": "Increased",
            }
        ),
        notification_frequency="1 Minute",
        emails=email
    )
    request.addfinalizer(alert.delete)
    setup_for_alerts(request, [alert], vm_name=vm.name)
    wait_for_ssa_enabled(vm)
    sockets_count = vm.configuration.hw.sockets

    for i in range(1, 3):
        do_scan(vm, rediscover=False)
        vm.reconfigure(changes={
            "cpu": True, "sockets": str(sockets_count + i),
            "disks": (),
            "network_adapters": ()
        })
        service_request = appliance.collections.requests.instantiate(
            description=service_request_desc.format(vm.name, sockets_count + i))
        service_request.wait_for_request(method="ui", num_sec=300, delay=10)
    wait_for_alert(
        smtp_test,
        alert,
        delay=30 * 60,
        additional_checks={"text": vm.name, "from_address": email}
    )
