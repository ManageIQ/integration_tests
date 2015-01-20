# -*- coding: utf-8 -*
from cfme.fixtures import pytest_selenium as sel
from utils.conf import ui_bench_tests
from utils.pagestats import analyze_page_stat
from utils.pagestats import navigate_accordions
from utils.pagestats import pages_to_csv
from utils.pagestats import pages_to_statistics_csv
from utils.pagestats import perf_click
from utils.pagestats import standup_perf_ui
from collections import OrderedDict
import pytest
import re

reports_filters = [
    re.compile(r'^POST \"\/report\/tree_select\/\?id\=[A-Za-z0-9\-\_]*\"$')]

chargeback_filters = [
    re.compile(r'^POST \"\/chargeback\/tree_select\/\?id\=[A-Za-z0-9\-\_]*\"$')]


@pytest.mark.bugzilla(1174300)
@pytest.mark.perf_ui_intelligence
@pytest.mark.usefixtures("cfme_log_level_rails_debug")
def test_perf_ui_intelligence_reports(ssh_client, soft_assert):
    pages, ui_worker_pid, prod_tail = standup_perf_ui(ssh_client, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'reports'), soft_assert))

    reports_acc = OrderedDict((('Saved Reports', 'saved_reports'), ('Reports', 'reports'),
        ('Schedules', 'schedules'), ('Dashboards', 'dashboards'),
        ('Dashboard Widgets', 'dashboard_widgets'), ('Edit Report Menus', 'edit_report_menus'),
        ('Import/Export', 'import_export')))

    pages.extend(navigate_accordions(reports_acc, 'reports', (ui_bench_tests['page_check']
        ['intelligence']['reports']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_intelligence_reports.csv')
    pages_to_statistics_csv(pages, reports_filters, 'statistics.csv')


@pytest.mark.perf_ui_intelligence
@pytest.mark.usefixtures("cfme_log_level_rails_debug")
def test_perf_ui_intelligence_chargeback(ssh_client, soft_assert):
    pages, ui_worker_pid, prod_tail = standup_perf_ui(ssh_client, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'chargeback'), soft_assert))

    charge_acc = OrderedDict((('Reports', 'reports'), ('Rates', 'rates'),
        ('Assignments', 'assignments')))

    pages.extend(navigate_accordions(charge_acc, 'chargeback', (ui_bench_tests['page_check']
        ['intelligence']['chargeback']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_intelligence_chargeback.csv')
    pages_to_statistics_csv(pages, chargeback_filters, 'statistics.csv')
