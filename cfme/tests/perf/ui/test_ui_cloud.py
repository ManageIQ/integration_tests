# -*- coding: utf-8 -*
"""UI performance tests on Cloud."""
from __future__ import unicode_literals
from cfme.cloud.provider import get_all_providers as get_all_cloud_provs
from cfme.fixtures import pytest_selenium as sel
from utils.blockers import BZ
from utils.conf import perf_tests
from utils.pagestats import analyze_page_stat
from utils.pagestats import navigate_accordions
from utils.pagestats import navigate_quadicons
from utils.pagestats import navigate_split_table
from utils.pagestats import pages_to_csv
from utils.pagestats import pages_to_statistics_csv
from utils.pagestats import perf_click
from utils.pagestats import standup_perf_ui
from collections import OrderedDict
import pytest
import re

cloud_provider_filters = [
    re.compile(r'^GET \"\/ems_cloud\/show\/[A-Za-z0-9]*\"$')]

availability_zones_filters = [
    re.compile(r'^GET \"\/availability_zone\/show\/[A-Za-z0-9]*\"$')]

tenants_filters = [
    re.compile(r'^GET \"\/cloud_tenant\/show\/[A-Za-z0-9]*\"$')]

flavors_filters = [
    re.compile(r'^GET \"\/flavor\/show\/[A-Za-z0-9]*\"$')]

security_groups_filters = [
    re.compile(r'^GET \"\/security_group\/show\/[A-Za-z0-9]*\"$')]

vm_cloud_filters = [
    re.compile(r'^POST \"\/vm_cloud\/tree_select\/\?id\=v\-[A-Za-z0-9]*\"$'),
    re.compile(r'^POST \"\/vm_cloud\/tree_select\/\?id\=t\-[A-Za-z0-9]*\"$'),
    re.compile(r'^POST \"\/vm_cloud\/tree_select\/\?id\=ms\-[A-Za-z0-9]*\"$')]


@pytest.mark.tier(3)
@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers", "cfme_log_level_rails_debug")
def test_perf_ui_cloud_providers(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'providers' in perf_tests['ui']['page_check']['cloud']:
        nav_limit = perf_tests['ui']['page_check']['cloud']['providers']

    pages.extend(navigate_quadicons(get_all_cloud_provs(), 'cloud_prov', 'clouds_providers',
        nav_limit, ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_cloud_providers.csv')
    pages_to_statistics_csv(pages, cloud_provider_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers", "cfme_log_level_rails_debug")
def test_perf_ui_cloud_availability_zones(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'availability_zones' in perf_tests['ui']['page_check']['cloud']:
        nav_limit = perf_tests['ui']['page_check']['cloud']['availability_zones']

    from cfme.cloud.availability_zone import list_page as lst_pg

    pages.extend(navigate_split_table(lst_pg.zone_table, 'clouds_availability_zones', nav_limit,
        ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_cloud_availability_zones.csv')
    pages_to_statistics_csv(pages, availability_zones_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers", "cfme_log_level_rails_debug")
def test_perf_ui_cloud_tenants(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'tenants' in perf_tests['ui']['page_check']['cloud']:
        nav_limit = perf_tests['ui']['page_check']['cloud']['tenants']

    from cfme.cloud.tenant import list_page as lst_pg

    pages.extend(navigate_split_table(lst_pg.tenant_table, 'clouds_tenants', nav_limit,
        ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_cloud_tenants.csv')
    pages_to_statistics_csv(pages, tenants_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers", "cfme_log_level_rails_debug")
def test_perf_ui_cloud_flavors(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'flavors' in perf_tests['ui']['page_check']['cloud']:
        nav_limit = perf_tests['ui']['page_check']['cloud']['flavors']

    from cfme.cloud.flavor import list_page as lst_pg

    pages.extend(navigate_split_table(lst_pg.flavor_table, 'clouds_flavors', nav_limit,
        ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_cloud_flavors.csv')
    pages_to_statistics_csv(pages, flavors_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers", "cfme_log_level_rails_debug")
def test_perf_ui_cloud_security_groups(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'security_groups' in perf_tests['ui']['page_check']['cloud']:
        nav_limit = perf_tests['ui']['page_check']['cloud']['security_groups']

    from cfme.cloud.security_group import list_page as lst_pg

    pages.extend(navigate_split_table(lst_pg.security_group_table, 'clouds_security_groups',
        nav_limit, ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_cloud_security_groups.csv')
    pages_to_statistics_csv(pages, security_groups_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
# Currently unskip 1170778 since a large environment is a requirement for this bug
@pytest.mark.meta(blockers=[BZ(1170778, unblock=True)])
@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers", "cfme_log_level_rails_debug")
def test_perf_ui_cloud_vm_explorer(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'clouds_instances'), soft_assert))

    cloud_acc = OrderedDict((('Instances by Provider', 'instances_by_prov'),
        ('Images by Provider', 'images_by_prov'), ('Instances', 'instances'), ('Images', 'images')))

    pages.extend(navigate_accordions(cloud_acc, 'clouds_instances', (perf_tests['ui']['page_check']
        ['cloud']['vm_explorer']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_cloud_vm_explorer.csv')
    pages_to_statistics_csv(pages, vm_cloud_filters, 'ui-statistics.csv')
