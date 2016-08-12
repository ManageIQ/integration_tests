# -*- coding: utf-8 -*
"""UI performance tests on Configure."""
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

configuration_filters = [
    re.compile(r'^POST \"\/ops\/tree_select\/\?id\=u\-[0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/ops\/tree_select\/\?id\=g\-[0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/ops\/tree_select\/\?id\=ti\-[0-9\-\_]*\"$')]


@pytest.mark.tier(3)
@pytest.mark.perf_ui_configure
@pytest.mark.usefixtures("cfme_log_level_rails_debug")
def test_perf_ui_configure_configuration(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'configuration'), soft_assert))

    services_acc = OrderedDict((('Settings', 'settings'), ('Access Control', 'access_control'),
        ('Diagnostics', 'diagnostics')))
    #    ('Database', 'database'))) - Requires almost 17 minutes to read the database tree.

    pages.extend(navigate_accordions(services_acc, 'configuration', (perf_tests['ui']['page_check']
        ['configure']['configuration']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_configure_configuration.csv')
    pages_to_statistics_csv(pages, configuration_filters, 'ui-statistics.csv')
