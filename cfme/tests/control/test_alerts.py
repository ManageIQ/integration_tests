# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from datetime import datetime, timedelta

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.control.explorer import alert_profiles, policies
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import ports
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.hosts import setup_host_creds
from cfme.utils.log import logger
from cfme.utils.net import net_check
from cfme.utils.providers import ProviderFilter
from cfme.utils.ssh import SSHClient
from cfme.utils.update import update
from cfme.utils.wait import wait_for
from markers.env_markers.provider import providers
from . import do_scan, wait_for_ssa_enabled


pf1 = ProviderFilter(classes=[InfraProvider])
pf2 = ProviderFilter(classes=[SCVMMProvider], inverted=True)

CANDU_PROVIDER_TYPES = [VMwareProvider]  # TODO: rhevm

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+automate", "+smartproxy", "+notifier"]),
    pytest.mark.uncollectif(BZ(1491576, forced_streams=['5.7']).blocks, 'BZ 1491576'),
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


@pytest.fixture(scope="module")
def policy_profile_collection(appliance):
    return appliance.collections.policy_profiles


@pytest.fixture(scope="module")
def policy_collection(appliance):
    return appliance.collections.policies


@pytest.fixture(scope="module")
def action_collection(appliance):
    return appliance.collections.actions


@pytest.fixture(scope="module")
def alert_collection(appliance):
    return appliance.collections.alerts


@pytest.fixture(scope="module")
def alert_profile_collection(appliance):
    return appliance.collections.alert_profiles


@pytest.fixture(scope="module")
def requests_collection(appliance):
    return appliance.collections.requests


@pytest.fixture(scope="function")
def vddk_url(provider):
    try:
        major, minor = str(provider.version).split(".")
    except ValueError:
        major = str(provider.version)
        minor = "0"
    vddk_version = "v{}_{}".format(major, minor)
    try:
        return cfme_data.get("basic_info").get("vddk_url").get(vddk_version)
    except AttributeError:
        pytest.skip("There is no vddk url for this VMware provider version")


@pytest.yield_fixture(scope="function")
def configure_fleecing(appliance, provider, vm, vddk_url):
    host = vm.get_detail(properties=("Relationships", "Host"))
    setup_host_creds(provider.key, host)
    appliance.install_vddk(vddk_url=vddk_url)
    yield
    appliance.uninstall_vddk()
    setup_host_creds(provider.key, host, remove_creds=True)


@pytest.fixture
def setup_for_alerts(alert_profile_collection, action_collection, policy_collection,
        policy_profile_collection):
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
        alert_profile = alert_profile_collection.create(
            alert_profiles.VMInstanceAlertProfile,
            "Alert profile for {}".format(vm_name),
            alerts=alerts_list
        )
        request.addfinalizer(alert_profile.delete)
        alert_profile.assign_to("The Enterprise")
        if event is not None:
            action = action_collection.create(
                "Evaluate Alerts for {}".format(vm_name),
                "Evaluate Alerts",
                action_values={"alerts_to_evaluate": alerts_list}
            )
            request.addfinalizer(action.delete)
            policy = policy_collection.create(
                policies.VMControlPolicy,
                "Evaluate Alerts policy for {}".format(vm_name),
                scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm_name)
            )
            request.addfinalizer(policy.delete)
            policy_profile = policy_profile_collection.create(
                "Policy profile for {}".format(vm_name), policies=[policy]
            )
            request.addfinalizer(policy_profile.delete)
            policy.assign_actions_to_event(event, [action])
            provider.assign_policy_profiles(policy_profile.description)
            request.addfinalizer(
                lambda: provider.unassign_policy_profiles(policy_profile.description))
    return _setup_for_alerts


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
def wait_candu(vm):
    vm.wait_candu_data_available(timeout=20 * 60)


@pytest.fixture(scope="module")
def vm_name():
    return random_vm_name(context="alert")


@pytest.yield_fixture(scope="function")
def vm(vm_name, full_template, provider, setup_provider):
    vm_obj = VM.factory(vm_name, provider, template_name=full_template.name)
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
            username=credentials[full_template.creds]['username'],
            password=credentials[full_template.creds]['password'],
            hostname=provider.mgmt.get_ip_address(vm_name)) as ssh_client:
        yield ssh_client


@pytest.yield_fixture(scope="module")
def setup_snmp(appliance):
    appliance.ssh_client.run_command("echo 'disableAuthorization yes' >> /etc/snmp/snmptrapd.conf")
    appliance.ssh_client.run_command("systemctl start snmptrapd.service")
    yield
    appliance.ssh_client.run_command("systemctl stop snmptrapd.service")
    appliance.ssh_client.run_command("sed -i '$ d' /etc/snmp/snmptrapd.conf")


@pytest.mark.provider(gen_func=providers, filters=[pf1, pf2], scope="module")
def test_alert_vm_turned_on_more_than_twice_in_past_15_minutes(request, provider, vm, smtp_test,
        register_event, alert_collection, setup_for_alerts):
    """ Tests alerts for vm turned on more than twice in 15 minutes

    Metadata:
        test_flag: alerts, provision
    """
    alert = alert_collection.create("VM Power On > 2 in last 15 min")
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


@pytest.mark.provider(CANDU_PROVIDER_TYPES)
def test_alert_rtp(request, vm, smtp_test, provider, setup_candu, wait_candu, setup_for_alerts,
        alert_collection):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    email = fauxfactory.gen_email()
    alert = alert_collection.create(
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
    request.addfinalizer(alert.delete)

    setup_for_alerts(request, [alert])
    wait_for_alert(smtp_test, alert, delay=30 * 60, additional_checks={
        "text": vm.name, "from_address": email})


@pytest.mark.provider(CANDU_PROVIDER_TYPES)
def test_alert_timeline_cpu(request, vm, set_performance_capture_threshold, provider, ssh,
        setup_candu, wait_candu, setup_for_alerts, alert_collection):
    """ Tests a custom alert that uses C&U data to trigger an alert. It will run a script that makes
    a CPU spike in the machine to trigger the threshold. The alert is displayed in the timelines.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    alert = alert_collection.create(
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


@pytest.mark.provider(CANDU_PROVIDER_TYPES)
def test_alert_snmp(request, appliance, provider, setup_snmp, setup_candu, vm, wait_candu,
        alert_collection, setup_for_alerts):
    """ Tests a custom alert that uses C&U data to trigger an alert. Since the threshold is set to
    zero, it will start firing mails as soon as C&U data are available. It uses SNMP to catch the
    alerts. It uses SNMP v2.

    Metadata:
        test_flag: alerts, provision, metrics_collection
    """
    match_string = fauxfactory.gen_alpha(length=8)
    alert = alert_collection.create(
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


@pytest.mark.provider(CANDU_PROVIDER_TYPES)
def test_alert_hardware_reconfigured(request, configure_fleecing, alert_collection, vm, smtp_test,
        requests_collection, setup_for_alerts):
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
    """
    email = fauxfactory.gen_email()
    service_request_desc = ("VM Reconfigure for: {0} - Processor Sockets: {1}, "
        "Processor Cores Per Socket: 1, Total Processors: {1}")
    alert = alert_collection.create(
        "Trigger by hardware reconfigured {}".format(fauxfactory.gen_alpha(length=4)),
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
    vm.power_control_from_provider("Power Off")
    for i in range(1, 3):
        do_scan(vm, rediscover=False)
        vm.reconfigure(changes={"cpu": True, "sockets": str(sockets_count + i), "disks": ()})
        service_request = requests_collection.instantiate(
            description=service_request_desc.format(vm.name, sockets_count + i))
        service_request.wait_for_request(method="ui", num_sec=300, delay=10)
    wait_for_alert(
        smtp_test,
        alert,
        delay=30 * 60,
        additional_checks={"text": vm.name, "from_address": email}
    )
