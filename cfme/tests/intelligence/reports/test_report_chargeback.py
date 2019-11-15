import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback,
]


def _cleanup_report(report):
    try:
        logger.info('Cleaning up report %s', report.menu_name)
        report.delete()
    except Exception:
        logger.warning('Failed to clean up report %s', report.menu_name)


# These tests are meant to catch issues such as BZ 1203022
def test_charge_report_filter_owner(appliance, infra_provider, request):
    """Tests creation of chargeback report that is filtered by owner


    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """

    report = appliance.collections.reports.create(
        menu_name=fauxfactory.gen_alphanumeric(),
        title=fauxfactory.gen_alphanumeric(),
        base_report_on="Chargeback for Vms",
        report_fields=[
            "Network I/O Used",
            "Network I/O Used Cost",
            "Storage Used",
            "Storage Used Cost",
            "Disk I/O Used",
            "Disk I/O Used Cost",
            "Owner",
            "Total Cost",
        ],
        filter=dict(
            filter_show_costs="Owner",
            filter_owner="Administrator"
        )
    )

    def cleanup_report(report):
        return lambda: _cleanup_report(report)

    request.addfinalizer(cleanup_report(report))
    report.queue(wait_for_finish=True)


def test_charge_report_filter_tag(appliance, infra_provider, request):
    """Tests creation of chargeback report that is filtered by tag


    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: low
        initialEstimate: 1/12h
    """

    report = appliance.collections.reports.create(
        menu_name=fauxfactory.gen_alphanumeric(),
        title=fauxfactory.gen_alphanumeric(),
        base_report_on="Chargeback for Vms",
        report_fields=[
            "CPU Used",
            "CPU Used Cost",
            "Memory Used",
            "Memory Used Cost",
            "Owner",
            "vCPUs Allocated Cost",
            "Total Cost",
        ],
        filter=dict(
            filter_show_costs="My Company Tag",
            filter_tag_cat="Location",
            filter_tag_value="Chicago"
        )
    )

    def cleanup_report(report):
        return lambda: _cleanup_report(report)

    request.addfinalizer(cleanup_report(report))

    report.queue(wait_for_finish=True)
