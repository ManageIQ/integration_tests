# -*- coding: utf-8 -*
"""UI performance tests on Control."""
from __future__ import unicode_literals
from cfme.fixtures import pytest_selenium as sel
from utils.conf import perf_tests
from utils.pagestats import analyze_page_stat
from utils.pagestats import navigate_accordions
from utils.pagestats import pages_to_csv
from utils.pagestats import pages_to_statistics_csv
from utils.pagestats import perf_click
from utils.pagestats import standup_perf_ui
from collections import OrderedDict
import pytest
import re

explorer_filters = [
    re.compile(r'^POST \"\/miq_policy\/tree_select\/\?id\=xx\-compliance[A-Za-z0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/miq_policy\/tree_select\/\?id\=xx\-control[A-Za-z0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/miq_policy\/tree_select\/\?id\=ev\-[0-9]*\"$'),
    re.compile(r'^POST \"\/miq_policy\/tree_select\/\?id\=a\-[0-9]*\"$'),
    re.compile(r'^POST \"\/miq_policy\/tree_select\/\?id\=al\-[0-9]*\"$')]


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1182271])
@pytest.mark.perf_ui_control
@pytest.mark.usefixtures("cfme_log_level_rails_debug")
def test_perf_ui_control_explorer(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'control_explorer'), soft_assert))

    services_acc = OrderedDict((('Policy Profiles', 'policy_profiles'), ('Policies', 'policies'),
        ('Events', 'events'), ('Conditions', 'conditions'), ('Actions', 'actions'),
        ('Alert Profiles', 'alert_profiles'), ('Alerts', 'alerts')))

    pages.extend(navigate_accordions(services_acc, 'control_explorer', (perf_tests['ui']
        ['page_check']['control']['explorer']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_control_explorer.csv')
    pages_to_statistics_csv(pages, explorer_filters, 'ui-statistics.csv')
