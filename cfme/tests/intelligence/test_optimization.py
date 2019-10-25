from cfme import test_requirements

pytestmark = [test_requirements.report]


def test_optimization_report_queue(appliance):
    """
    Polarion:
        assignee: pvala
        initialEstimate: 1/8h
        casecomponent: Reporting
        tags: reports
    """
    optimization_report = appliance.collections.optimization_reports.instantiate(
        menu_name="Host CPU Trends (last week)"
    )
    saved_report = optimization_report.queue()
    assert saved_report.exists
