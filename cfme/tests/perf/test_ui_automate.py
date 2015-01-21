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

explorer_filters = [
    re.compile(r'^POST \"\/miq_ae_class\/tree_select\/\?id\=aem\-[A-Za-z0-9\-\_]*\"$'),
    re.compile(r'^POST \"\/miq_ae_class\/tree_select\/\?id\=aei\-[A-Za-z0-9\-\_]*\"$')]

customization_filters = [
    re.compile(r'^POST \"\/miq_ae_customization\/tree_select\/\?id\=odg\-[A-Za-z0-9\-\_]*\"$')]


@pytest.mark.perf_ui_automate
@pytest.mark.usefixtures("cfme_log_level_rails_debug")
def test_perf_ui_automate_explorer(ui_worker_pid, ssh_client, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, ssh_client, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'automate_explorer'), soft_assert))

    services_acc = OrderedDict((('Datastore', 'datastore'), ))

    pages.extend(navigate_accordions(services_acc, 'automate_explorer',
        ui_bench_tests['page_check']['automate']['explorer'], ui_worker_pid, prod_tail,
        soft_assert))

    pages_to_csv(pages, 'perf_ui_automate_explorer.csv')
    pages_to_statistics_csv(pages, explorer_filters, 'statistics.csv')


@pytest.mark.perf_ui_automate
@pytest.mark.usefixtures("cfme_log_level_rails_debug")
def test_perf_ui_automate_customization(ui_worker_pid, ssh_client, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, ssh_client, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'automate_customization'), soft_assert))

    services_acc = OrderedDict((('Provisioning Dialogs', 'provisioning_dialogs'),
        ('Service Dialogs', 'service_dialogs'), ('Buttons', 'buttons'),
        ('Import/Export', 'import_export')))

    pages.extend(navigate_accordions(services_acc, 'automate_customization',
        ui_bench_tests['page_check']['automate']['customization'], ui_worker_pid, prod_tail,
        soft_assert))

    pages_to_csv(pages, 'perf_ui_automate_customization.csv')
    pages_to_statistics_csv(pages, customization_filters, 'statistics.csv')
