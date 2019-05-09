# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.intelligence.reports.reports import ImportExportCustomReportsView
from cfme.intelligence.reports.widgets import ImportExportWidgetsCommitView
from cfme.utils.path import data_path

pytestmark = [pytest.mark.tier(1), test_requirements.report]


@pytest.fixture()
def widget_file(appliance):
    file_path = data_path.join("ui/intelligence/import_widget.yaml").realpath().strpath
    widget = appliance.collections.dashboard_report_widgets.instantiate(
        appliance.collections.dashboard_report_widgets.CHART,
        "testing widget",
        description="testing widget description",
        filter="Configuration Management/Virtual Machines/Guest OS Information - any OS",
        active=True,
    )

    yield file_path, widget

    # delete the widget in case it was imported or created
    widget.delete_if_exists()


@pytest.fixture(scope="function")
def report_file(appliance):
    file_path = data_path.join("ui/intelligence/import_report.yaml").realpath().strpath
    report = appliance.collections.reports.instantiate(
        type="My Company (All Groups)",
        subtype="Custom",
        menu_name="testing report",
        title="testing report title",
    )

    yield file_path, report

    # delete the report in case it was imported or created
    report.delete_if_exists()


def test_import_widget(appliance, widget_file):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/16h
        startsin: 5.3
        testSteps:
            1. Import the widget data yaml.
            2. Check if widget created with import is same as the expected widget.
    """
    file_path, widget = widget_file
    collection = appliance.collections.dashboard_report_widgets

    collection.import_widget(file_path)
    import_view = collection.create_view(ImportExportWidgetsCommitView)
    import_view.flash.assert_message("imported successfully", partial=True)

    assert widget.exists


def test_export_widget(appliance, widget_file):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/16h
        startsin: 5.3
    """
    _, widget = widget_file
    collection = appliance.collections.dashboard_report_widgets
    collection.create(
        widget_class=getattr(collection, widget.TITLE.upper()),
        title=widget.title,
        description=widget.description,
        filter=widget.filter,
        active=widget.active,
    )
    collection.export_widget(widget.title)


def test_import_report(appliance, report_file):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/2h
        testSteps:
            1. Import the report data yaml.
            2. Check if report created with import is same as the expected report.

    """
    file_path, report = report_file
    collection = appliance.collections.reports

    collection.import_report(file_path)
    view = collection.create_view(ImportExportCustomReportsView)
    assert view.is_displayed
    view.flash.assert_message("Imported Report: ", partial=True)

    assert report.exists


def test_export_report(appliance, report_file):
    """
    Polarion:
        assignee: pvala
        casecomponent: Reporting
        initialEstimate: 1/16h
        startsin: 5.3
    """
    _, report = report_file
    collection = appliance.collections.reports
    collection.create(
        menu_name=report.menu_name,
        title=report.title,
        base_report_on="VMs and Instances",
        report_fields=["Archived", "Autostart", "Boot Time"],
    )
    collection.export_report(report.menu_name)
