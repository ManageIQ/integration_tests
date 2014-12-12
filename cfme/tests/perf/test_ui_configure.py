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

configuration_filters = [
    re.compile(r'^POST \"\/ops\/tree_select\/\?id\=u\-[0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/ops\/tree_select\/\?id\=g\-[0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/ops\/tree_select\/\?id\=ti\-[0-9\-\_]*\"$')]


@pytest.mark.perf_ui_configure
def test_perf_ui_configure_configuration(ssh_client, soft_assert):
    pages, ui_worker_pid, prod_tail = standup_perf_ui(ssh_client, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'configuration'), soft_assert))

    services_acc = OrderedDict((('Settings', 'settings'), ('Access Control', 'access_control'),
        ('Diagnostics', 'diagnostics')))
    #    ('Database', 'database'))) - Requires almost 17 minutes to read the database tree.

    pages.extend(navigate_accordions(services_acc, 'configuration', (ui_bench_tests['page_check']
        ['configure']['configuration']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_configure_configuration.csv')
    pages_to_statistics_csv(pages, configuration_filters, 'statistics.csv')
