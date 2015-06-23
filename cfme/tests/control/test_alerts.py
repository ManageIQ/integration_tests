# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.control import explorer
from cfme.infrastructure import provider
from utils import testgen
from utils.log import logger
from utils.providers import setup_provider
from utils.update import update
from utils.virtual_machines import deploy_template
from utils.wait import wait_for


pytestmark = [pytest.mark.long_running]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc,
        'small_template', scope="module", template_location=["small_template"])
    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if args["provider_type"] in {"scvmm"}:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def wait_for_alert(smtp, alert, delay=None):
    """DRY waiting function

    Args:
        smtp: smtp_test funcarg
        alert: Alert name
        delay: Optional delay to pass to wait_for
    """
    logger.info("Waiting for informative e-mail of alert '{}' to come".format(alert.description))

    def _mail_arrived():
        for mail in smtp.get_emails():
            if "Alert Triggered: {}".format(alert.description) in mail["subject"]:
                return True
        return False
    wait_for(
        _mail_arrived,
        num_sec=delay,
        delay=5,
        message="wait for e-mail to come!"
    )


def setup_for_alerts(request, alerts, event, vm_name, provider_data, provider_key):
    """This function takes alerts and sets up CFME for testing it

    Args:
        request: py.test funcarg request
        alerts: Alert objects
        event: Event to hook on (VM Power On, ...)
        vm_name: VM name to use for policy filtering
        provider_data: funcarg provider_data
    """
    setup_provider(provider_key)
    alert_profile = explorer.VMInstanceAlertProfile(
        "Alert profile for %s" % vm_name,
        alerts
    )
    alert_profile.create()
    request.addfinalizer(alert_profile.delete)
    alert_profile.assign_to("The Enterprise")
    action = explorer.Action(
        "Evaluate Alerts for %s" % vm_name,
        "Evaluate Alerts",
        alerts
    )
    action.create()
    request.addfinalizer(action.delete)
    policy = explorer.VMControlPolicy(
        "Evaluate Alerts policy for %s" % vm_name,
        scope="fill_field(VM and Instance : Name, INCLUDES, %s)" % vm_name
    )
    policy.create()
    request.addfinalizer(policy.delete)
    policy_profile = explorer.PolicyProfile(
        "Policy profile for %s" % vm_name, [policy]
    )
    policy_profile.create()
    request.addfinalizer(policy_profile.delete)
    policy.assign_actions_to_event(event, [action])
    prov = provider.Provider(provider_data["name"])
    prov.assign_policy_profiles(policy_profile.description)


@pytest.yield_fixture(scope="module")
def vm_name(provider_key, provider_mgmt, small_template):
    name = "test_alerts_{}".format(fauxfactory.gen_alpha())
    try:
        name = deploy_template(
            provider_key, name, template_name=small_template, allow_skip="default")
        yield name
    finally:
        try:
            if provider_mgmt.does_vm_exist(name):
                provider_mgmt.delete_vm(name)
        except Exception as e:
            logger.exception(e)


@pytest.mark.meta(server_roles=["+automate", "+notifier"])
def test_alert_vm_turned_on_more_than_twice_in_past_15_minutes(
        vm_name, provider_crud, provider_data, provider_mgmt, provider_type, request, smtp_test,
        provider_key, register_event):
    """ Tests alerts for vm turned on more than twice in 15 minutes

    Metadata:
        test_flag: alerts, provision
    """
    alert = explorer.Alert("VM Power On > 2 in last 15 min")
    with update(alert):
        alert.emails = "test@test.test"

    setup_for_alerts(
        request, [alert], "VM Power On", vm_name, provider_data, provider_key)

    # Ok, hairy stuff done, now - hammertime!
    register_event(
        provider_crud.get_yaml_data()['type'],
        "vm", vm_name, ["vm_power_off"])
    register_event(
        provider_crud.get_yaml_data()['type'],
        "vm", vm_name, ["vm_power_on"])
    # We don't check for *_req events because these happen only if the operation is issued via CFME.
    provider_mgmt.stop_vm(vm_name)
    wait_for(lambda: provider_mgmt.is_vm_stopped(vm_name), num_sec=240)
    for i in range(5):
        provider_mgmt.start_vm(vm_name)
        wait_for(lambda: provider_mgmt.is_vm_running(vm_name), num_sec=240)
        provider_mgmt.stop_vm(vm_name)
        wait_for(lambda: provider_mgmt.is_vm_stopped(vm_name), num_sec=240)

    wait_for_alert(smtp_test, alert, delay=16 * 60)
