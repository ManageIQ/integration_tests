# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from datetime import datetime, timedelta

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.configure.configuration import server_roles_enabled
from cfme.configure.configuration.region_settings import CANDUCollection
from cfme.control.explorer import actions, alert_profiles, alerts, policies, policy_profiles
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import ports, testgen
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.net import net_check
from cfme.utils.providers import ProviderFilter
from cfme.utils.ssh import SSHClient
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+automate", "+notifier"]),
    pytest.mark.tier(3),
    test_requirements.alert
]

CANDU_PROVIDER_TYPES = [VMwareProvider]  # TODO: rhevm


pf1 = ProviderFilter(classes=[InfraProvider])
pf2 = ProviderFilter(classes=[SCVMMProvider], inverted=True)
pytest_generate_tests = testgen.generate(
    gen_func=testgen.providers,
    filters=[pf1, pf2],
    scope="module"
)


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
    alert_profile = alert_profiles.VMInstanceAlertProfile(
        "Alert profile for {}".format(vm_name),
        alerts
    )
    alert_profile.create()
    request.addfinalizer(alert_profile.delete)
    alert_profile.assign_to("The Enterprise")
    if event is not None:
        action = actions.Action(
            "Evaluate Alerts for {}".format(vm_name),
            "Evaluate Alerts",
            action_values={"alerts_to_evaluate": alerts}
        )
        action.create()
        request.addfinalizer(action.delete)
        policy = policies.VMControlPolicy(
            "Evaluate Alerts policy for {}".format(vm_name),
            scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
        )
        policy.create()
        request.addfinalizer(policy.delete)
        policy_profile = policy_profiles.PolicyProfile(
            "Policy profile for {}".format(vm_name), [policy]
        )
        policy_profile.create()
        request.addfinalizer(policy_profile.delete)
        policy.assign_actions_to_event(event, [action])
        provider.assign_policy_profiles(policy_profile.description)
        request.addfinalizer(lambda: provider.unassign_policy_profiles(policy_profile.description))


@pytest.yield_fixture(scope="module")
def set_performance_capture_threshold(appliance):
    yaml = appliance.get_yaml_config()
    yaml["performance"]["capture_threshold_with_alerts"]["vm"] = "3.minutes"
    appliance.set_yaml_config(yaml)
    yield
    yaml = appliance.get_yaml_config()
    yaml["performance"]["capture_threshold_with_alerts"]["vm"] = "20.minutes"
    appliance.set_yaml_config(yaml)


@pytest.yield_fixture(scope="module")
def setup_candu():
    candu = CANDUCollection()
    candu.enable_all()
    with server_roles_enabled('ems_metrics_coordinator', 'ems_metrics_collector',
            'ems_metrics_processor'):
        yield
    candu.disable_all()


@pytest.fixture(scope="function")
def wait_candu(vm):
    vm.wait_candu_data_available(timeout=20 * 60)


@pytest.fixture(scope="module")
def vm_name():
    return random_vm_name(context="alert")


@pytest.yield_fixture(scope="function")
def vm(vm_name, full_template, provider, setup_provider):
    vm_obj = VM.factory(vm_name, provider, template_name=full_template)
    vm_obj.create_on_provider(allow_skip="default")
    provider.mgmt.start_vm(vm_obj.name)
    provider.mgmt.wait_vm_running(vm_obj.name)
    # In order to have seamless SSH connection
    vm_ip, _ = wait_for(
        lambda: provider.mgmt.current_ip_address(vm_obj.name),
        num_sec=300, delay=5, fail_condition={None}, message="wait for testing VM IP address.")
    wait_for(
        net_check, [ports.SSH, vm_ip], {"force": True},
        num_sec=300, delay=5, message="testing VM's SSH available")
    if not vm_obj.exists:
        provider.refresh_provider_relationships()
        vm_obj.wait_to_appear()
    yield vm_obj
    try:
        if provider.mgmt.does_vm_exist(vm_obj.name):
            provider.mgmt.delete_vm(vm_obj.name)
        provider.refresh_provider_relationships()
    except Exception as e:
        logger.exception(e)


@pytest.yield_fixture(scope="function")
def ssh(provider, full_template, vm_name):
    with SSHClient(
            username=credentials[full_template]['username'],
            password=credentials[full_template]['password'],
            hostname=provider.mgmt.get_ip_address(vm_name)) as ssh_client:
        yield ssh_client


@pytest.yield_fixture(scope="module")
def setup_snmp(appliance):
    appliance.ssh_client.run_command("echo 'disableAuthorization yes' >> /etc/snmp/snmptrapd.conf")
    appliance.ssh_client.run_command("systemctl start snmptrapd.service")
    yield
    appliance.ssh_client.run_command("systemctl stop snmptrapd.service")
    appliance.ssh_client.run_command("sed -i '$ d' /etc/snmp/snmptrapd.conf")


def test_alert_vm_turned_on_more_than_twice_in_past_15_minutes(request, provider, vm, smtp_test,
        register_event):
    """ Tests alerts for vm turned on more than twice in 15 minutes

    Metadata:
        test_flag: alerts, provision
    """
    alert = alerts.Alert("VM Power On > 2 in last 15 min")
    with update(alert):
        alert.active = True
        alert.emails = fauxfactory.gen_email()

    setup_for_alerts(request, [alert], "VM Power On", vm.name, provider)

    if not provider.mgmt.is_vm_stopped(vm.name):
        provider.mgmt.stop_vm(vm.name)
    provider.refresh_provider_relationships()

    # preparing events to listen to
    register_event(target_type='VmOrTemplate', target_name=vm.name,
                   event_type='request_vm_poweroff')
    register_event(target_type='VmOrTemplate', target_name=vm.name, event_type='vm_poweoff')

    vm.wait_for_vm_state_change(vm.STATE_OFF)
    for i in range(5):
        vm.power_control_from_cfme(option=vm.POWER_ON, cancel=False)
        register_event(target_type='VmOrTemplate', target_name=vm.name,
                       event_type='request_vm_start')
        register_event(target_type='VmOrTemplate', target_name=vm.name, event_type='vm_start')

        wait_for(lambda: provider.mgmt.is_vm_running(vm.name), num_sec=300)
        vm.wait_for_vm_state_change(vm.STATE_ON)
        vm.power_control_from_cfme(option=vm.POWER_OFF, cancel=False)
        register_event(target_type='VmOrTemplate', target_name=vm.name,
                       event_type='request_vm_poweroff')
        register_event(target_type='VmOrTemplate', target_name=vm.name, event_type='vm_poweroff')

        wait_for(lambda: provider.mgmt.is_vm_stopped(vm.name), num_sec=300)
        vm.wait_for_vm_state_change(vm.STATE_OFF)

    wait_for_alert(smtp_test, alert, delay=16 * 60)


@pytest.mark.uncollectif(lambda provider: not provider.one_of(*CANDU_PROVIDER_TYPES))
def test_alert_rtp(request, vm, smtp_test, provider, setup_candu, wait_candu):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    email = fauxfactory.gen_email()
    alert = alerts.Alert(
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
        "text": vm.name, "from_address": email})


@pytest.mark.uncollectif(lambda provider: not provider.one_of(*CANDU_PROVIDER_TYPES))
def test_alert_timeline_cpu(request, vm, set_performance_capture_threshold, provider, ssh,
        setup_candu, wait_candu):
    """ Tests a custom alert that uses C&U data to trigger an alert. It will run a script that makes
    a CPU spike in the machine to trigger the threshold. The alert is displayed in the timelines.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    alert = alerts.Alert(
        "TL event by CPU {}".format(fauxfactory.gen_alpha(length=4)),
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
    alert.create()
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert], vm_name=vm.name)
    # Generate a 100% CPU spike for 15 minutes, that should be noticed by CFME.
    ssh.cpu_spike(seconds=60 * 15, cpus=2, ensure_user=True)
    timeline = vm.open_timelines()
    timeline.filter.fill({
        "event_category": "Alarm/Status Change/Errors",
        "time_range": "Days",
        "calendar": "{dt.month}/{dt.day}/{dt.year}".format(dt=datetime.now() + timedelta(days=1))
    })
    timeline.filter.apply.click()
    events = timeline.chart.get_events()
    for event in events:
        if alert.description in event.message:
            break
    else:
        pytest.fail("The event has not been found on the timeline. Event list: {}".format(events))


@pytest.mark.uncollectif(lambda provider: not provider.one_of(*CANDU_PROVIDER_TYPES))
def test_alert_snmp(request, appliance, provider, setup_snmp, setup_candu, vm, wait_candu):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available. It uses SNMP to catch the
    alerts. It uses SNMP v2.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    match_string = fauxfactory.gen_alpha(length=8)
    alert = alerts.Alert(
        "Trigger by CPU {}".format(fauxfactory.gen_alpha(length=4)),
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
    alert.create()
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])

    def _snmp_arrived():
        rc, stdout = appliance.ssh_client.run_command(
            "journalctl --no-pager /usr/sbin/snmptrapd | grep {}".format(match_string))
        if rc != 0:
            return False
        elif stdout:
            return True
        else:
            return False

    wait_for(_snmp_arrived, timeout="30m", delay=60, message="SNMP trap arrived.")
