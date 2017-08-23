# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import cfme.web_ui.flash as flash

from cfme.intelligence.reports.reports import CustomReport
from cfme.utils.log import logger

pytestmark = [pytest.mark.tier(3)]


def _cleanup_report(report):
    try:
        logger.info('Cleaning up report %s', report.menu_name)
        report.delete()
    except:
        logger.warning('Failed to clean up report %s', report.menu_name)


# These tests are meant to catch issues such as BZ 1203022
def test_charge_report_filter_owner(infra_provider, request):
    """Tests creation of chargeback report that is filtered by owner

    """

    report = CustomReport(
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
    report.create()

    def cleanup_report(report):
        return lambda: _cleanup_report(report)

    request.addfinalizer(cleanup_report(report))

    flash.assert_message_match('Report "{}" was added'.format(report.menu_name))
    report.queue(wait_for_finish=True)


def test_charge_report_filter_tag(infra_provider, request):
    """Tests creation of chargeback report that is filtered by tag

    """

    report = CustomReport(
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
    report.create()

    def cleanup_report(report):
        return lambda: _cleanup_report(report)

    request.addfinalizer(cleanup_report(report))

    flash.assert_message_match('Report "{}" was added'.format(report.menu_name))
    report.queue(wait_for_finish=True)
