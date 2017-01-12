import fauxfactory
import pytest
from cfme.control import explorer
from utils import testgen
from utils.log import logger
from utils.version import current_version
from utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


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
        message="wait for e-mail to come! [{}]".format(alert.description)
    )


def setup_for_alerts(request, alerts, profile_name):
    """This function takes alerts and sets up CFME for testing it.

    Args:
        request: py.test funcarg request
        alerts: Alert objects
        profile_name: Alert profile name
    """
    alert_profile = explorer.MiddlewareServerAlertProfile(
        "Alert profile for {}".format(profile_name),
        alerts
    )
    alert_profile.create()
    request.addfinalizer(alert_profile.delete)
    alert_profile.assign_to("The Enterprise")


@pytest.mark.meta(server_roles=["+automate", "+notifier"])
def test_mw_alerts(provider, request, smtp_test):
    """ Tests set of middleware alerts"""
    alerts_data = []
    # 'JVM heap used' alert test
    alerts_data.append((explorer.Alert(
        "MW Alert - JVM Heap used_{}".format(fauxfactory.gen_alpha(length=3)),
        active=True,
        based_on="Middleware Server",
        evaluate=(
            "JVM Heap Used",
            {
                "mw_value_greater_than": "30",
                "mw_value_less_than": "29",
            }),
        notification_frequency="1 Minute",
        emails=fauxfactory.gen_email(),
    ),
        "MW Alert Profile - JVM Used",
        3 * 60))
    # 'JVM Non heap used' alert test
    alerts_data.append((explorer.Alert(
        "MW Alert - JVM Non Heap committed_{}".format(fauxfactory.gen_alpha(length=3)),
        active=True,
        based_on="Middleware Server",
        evaluate=(
            "JVM Non Heap Used",
            {
                "mw_value_greater_than": "21",
                "mw_value_less_than": "20",
            }),
        notification_frequency="1 Minute",
        emails=fauxfactory.gen_email(),
    ),
        "MW Alert Profile - JVM Non Heap Committed",
        3 * 60))
    # 'JVM Accumulated GC Duration' alert test
    alerts_data.append((explorer.Alert(
        "MW Alert - JVM Accumulated GC Duration_{}".format(fauxfactory.gen_alpha(length=3)),
        active=True,
        based_on="Middleware Server",
        evaluate=(
            "JVM Accumulated GC Duration",
            {
                "mw_operator": ">=",
                "mw_value_gc": "1",
            }),
        notification_frequency="1 Minute",
        emails=fauxfactory.gen_email(),
    ),
        "MW Alert Profile - JVM Accumulated GC Duration",
        3 * 60))

    for alert, profile_name, delay_time in alerts_data:
        alert.create()
        request.addfinalizer(alert.delete)
        setup_for_alerts(request, [alert], profile_name)
        wait_for_alert(smtp_test, alert, delay=delay_time)
