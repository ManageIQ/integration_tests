import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive #IGNORE:E1101
@pytest.mark.usefixtures("maximized")
class TestUtilization:
    def test_datastores(self, optimize_utilization_pg):
        Assert.true(optimize_utilization_pg.is_the_current_page)
        node_name = "datastore1"
        node_pg = optimize_utilization_pg.click_on_node(node_name)
        summary_pg = node_pg.click_on_summary()
        #Assert.true(summary_pg.tab_buttons.current_tab == "Summary")
        sum_trends = "2 Weeks"
        sum_classification = ""
        sum_time_zone = ""
        sum_date = "7/5/2013"
        initial_sum_date = summary_pg.date_field.get_attribute("value")
        summary_pg.fill_data(sum_trends, sum_classification, sum_time_zone, sum_date)
        if(summary_pg.date_field.get_attribute("value") == initial_sum_date):
             Assert.true(summary_pg.date_field.get_attribute("value") == sum_date, "There is no utilization date for the specified date")
        else:
            Assert.true(summary_pg.date_field.get_attribute("value") == sum_date)
        time.sleep(5)
        details_pg = summary_pg.click_on_details()
        #Assert.true(summary_pg.tab_buttons.current_tab == "Details")
        det_trends = "3 Weeks"
        det_classification = ""
        det_time_zone = ""
        details_pg.fill_data(det_trends, det_classification, det_time_zone)
        time.sleep(5)
        report_pg = details_pg.click_on_report()
        #Assert.true(summary_pg.tab_buttons.current_tab == "Report")
        rep_trends = "4 Weeks"
        rep_classification = ""
        rep_time_zone = ""
        rep_date = "7/5/2013"
        initial_rep_date = report_pg.date_field.get_attribute("value")
        report_pg.fill_data(rep_trends, rep_classification, rep_time_zone, rep_date)
        if(summary_pg.date_field.get_attribute("value") == initial_sum_date):
             Assert.true(report_pg.date_field.get_attribute("value") == rep_date, "There is no utilization date for the specified date")
        else:
            Assert.true(report_pg.date_field.get_attribute("value") == rep_date)
        Assert.true(report_pg.details.get_section("Basic Information").get_item("Utilization Trend Summary for").value == "Datastore [%s]" %node_name)

    def test_providers(self, optimize_utilization_pg):
        Assert.true(optimize_utilization_pg.is_the_current_page)
        node_name = "RHEV 3.1"
        node_pg = optimize_utilization_pg.click_on_node(node_name)
        summary_pg = node_pg.click_on_summary()
        #Assert.true(summary_pg.tab_buttons.current_tab == "Summary")
        sum_trends = "2 Weeks"
        sum_classification = ""
        sum_time_zone = ""
        sum_date = "7/5/2013"
        initial_sum_date = summary_pg.date_field.get_attribute("value")
        summary_pg.fill_data(sum_trends, sum_classification, sum_time_zone, sum_date)
        if(summary_pg.date_field.get_attribute("value") == initial_sum_date):
             Assert.true(summary_pg.date_field.get_attribute("value") == sum_date, "There is no utilization date for the specified date")
        else:
            Assert.true(summary_pg.date_field.get_attribute("value") == sum_date)
        time.sleep(5)
        details_pg = summary_pg.click_on_details()
        det_trends = "3 Weeks"
        det_classification = ""
        det_time_zone = ""
        details_pg.fill_data(det_trends, det_classification, det_time_zone)
        time.sleep(5)
        report_pg = details_pg.click_on_report()
        rep_trends = "4 Weeks"
        rep_classification = ""
        rep_time_zone = ""
        rep_date = "7/5/2013"
        initial_rep_date = report_pg.date_field.get_attribute("value")
        report_pg.fill_data(rep_trends, rep_classification, rep_time_zone, rep_date)
        if(summary_pg.date_field.get_attribute("value") == initial_sum_date):
             Assert.true(report_pg.date_field.get_attribute("value") == rep_date, "There is no utilization date for the specified date")
        else:
            Assert.true(report_pg.date_field.get_attribute("value") == rep_date)
        Assert.true(report_pg.details.get_section("Basic Information").get_item("Utilization Trend Summary for").value == "Management System [%s]" %node_name)


