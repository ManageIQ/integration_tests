import os

import pytest
import yaml

from cfme.utils.path import data_path


@pytest.fixture
def default_alerts(appliance):
    file_name = data_path.join('ui/control/default_alerts.yaml').strpath
    alerts = {}
    if os.path.exists(file_name):
        with open(file_name) as f:
            all_alerts = yaml.safe_load(f)
            alerts = (all_alerts.get('v5.10'))
    else:
        pytest.skip(f'Could not find {file_name}, skipping test.')

    # instantiate a list of alerts based on default_alerts.yaml
    alert_collection = appliance.collections.alerts
    default_alerts = [
        alert_collection.instantiate(
            description=alert.get('Description'),
            active=alert.get('Active'),
            based_on=alert.get('Based On'),
            evaluate=alert.get('What is evaluated'),
            emails=alert.get('Email'),
            snmp_trap=alert.get('SNMP'),
            timeline_event=alert.get('Event on Timeline'),
            mgmt_event=alert.get('Management Event Raised')
        )
        for key, alert in alerts.items()
    ]
    return default_alerts


@pytest.mark.smoke
def test_default_alerts(appliance, default_alerts):
    """ Tests the default pre-configured alerts on the appliance and
        ensures that they have not changed between versions.

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Control
    """
    # get the alerts of the appliance
    alerts = appliance.collections.alerts.all()
    # compare sorted lists to deal with unordered dictionary
    assert sorted(default_alerts) == sorted(alerts)
