# -*- coding: utf-8 -*
"""UI performance tests on Infrastructure."""
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.datastore import get_all_datastores
from cfme.infrastructure.host import get_all_hosts
from cfme.infrastructure.provider import get_all_providers
from cfme.web_ui import paginator
from utils.blockers import BZ
from utils.conf import perf_tests
from utils.pagestats import analyze_page_stat
from utils.pagestats import navigate_accordions
from utils.pagestats import navigate_quadicons
from utils.pagestats import pages_to_csv
from utils.pagestats import pages_to_statistics_csv
from utils.pagestats import perf_click
from utils.pagestats import standup_perf_ui
from collections import OrderedDict
import pytest
import re

infra_provider_filters = [
    re.compile(r'^GET \"\/ems_infra\/show\/[A-Za-z0-9]*\"$')]

cluster_filters = [
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\?display\=main\"$'),
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\?display\=config_info\"$'),
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\?display\=hosts\"$'),
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\?display\=all_vms\"$'),
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\?display\=miq_templates\"$'),
    re.compile(r'^GET \"\/ems_cluster\/show\/[A-Za-z0-9]*\?display\=resource_pools\"$')]

host_filters = [
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/host\/host_services\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=main\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=devices\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=network\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=os_info\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=hv_info\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=storages\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=vms\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=miq_templates\"$'),
    re.compile(r'^GET \"\/host\/show\/[A-Za-z0-9]*\?display\=storage_adapters\"$')]

vm_infra_filters = [
    re.compile(r'^POST \"\/vm_infra\/tree_select\/\?id\=v\-[0-9]*\"$'),
    re.compile(r'^POST \"\/vm_infra\/tree_select\/\?id\=t\-[0-9]*\"$'),
    re.compile(r'^POST \"\/vm_infra\/tree_select\/\?id\=ms\-[0-9]*\"$')]
#    re.compile(r'^POST \"\/vm_infra\/accordion_select\/\?id\=[A-Za-z\_0-9]*\"$')]

resource_pool_filters = [
    re.compile(r'^GET \"\/resource_pool\/show\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/resource_pool\/show\/[A-Za-z0-9]*\?display\=main\"$'),
    re.compile(r'^GET \"\/resource_pool\/show\/[A-Za-z0-9]*\?display\=all_vms\"$')]

storage_filters = [
    re.compile(r'^GET \"\/storage\/show\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/files\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/disk_files\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/snapshot_files\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/vm_ram_files\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/vm_misc_files\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/debris_files\/[A-Za-z0-9]*\"$'),
    re.compile(r'^GET \"\/storage\/show\/[A-Za-z0-9]*\?display\=main\"$'),
    re.compile(r'^GET \"\/storage\/show\/[A-Za-z0-9]*\?display\=hosts\"$'),
    re.compile(r'^GET \"\/storage\/show\/[A-Za-z0-9]*\?display\=all_vms\"$')]

infra_pxe_filters = [
    re.compile(r'^POST \"\/pxe\/tree_select\/\?id\=ct\-[0-9]*\"$'),
    re.compile(r'^POST \"\/pxe\/tree_select\/\?id\=pit\-[0-9]*\"$')]


@pytest.mark.tier(3)
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_providers(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'providers' in perf_tests['ui']['page_check']['infrastructure']:
        nav_limit = perf_tests['ui']['page_check']['infrastructure']['providers']

    pages.extend(navigate_quadicons(get_all_providers(), 'infra_prov', 'infrastructure_providers',
        nav_limit, ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_infra_providers.csv')
    pages_to_statistics_csv(pages, infra_provider_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_clusters(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'clusters' in perf_tests['ui']['page_check']['infrastructure']:
        nav_limit = perf_tests['ui']['page_check']['infrastructure']['clusters']

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'infrastructure_clusters'), soft_assert))

    clusters = set([])
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'ems_cluster/show')]"):
            clusters.add(sel.get_attribute(title, "title"))

    acc_bars = ['Properties', 'Relationships']

    pages.extend(navigate_quadicons(clusters, 'cluster', 'infrastructure_clusters', nav_limit,
        ui_worker_pid, prod_tail, soft_assert, acc_bars))

    pages_to_csv(pages, 'perf_ui_infra_clusters.csv')
    pages_to_statistics_csv(pages, cluster_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_hosts(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'hosts' in perf_tests['ui']['page_check']['infrastructure']:
        nav_limit = perf_tests['ui']['page_check']['infrastructure']['hosts']

    acc_bars = ['Properties', 'Relationships', 'Security', 'Configuration']

    pages.extend(navigate_quadicons(get_all_hosts(), 'host', 'infrastructure_hosts', nav_limit,
        ui_worker_pid, prod_tail, soft_assert, acc_bars))

    pages_to_csv(pages, 'perf_ui_infra_hosts.csv')
    pages_to_statistics_csv(pages, host_filters, 'ui-statistics.csv')


# Currently unskip on 1175504 since a large environment is a requirement for this bug
@pytest.mark.tier(3)
@pytest.mark.meta(
    blockers=[
        1086386,
        BZ(1175504, unblock=True)
    ]
)
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_vm_explorer(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'infrastructure_virtual_machines'), soft_assert))

    infra_acc = OrderedDict((('VMs & Templates', 'vms_and_templates'), ('VMs', 'vms'),
        ('Templates', 'templates')))

    pages.extend(navigate_accordions(infra_acc, 'infrastructure_virtual_machines',
        perf_tests['ui']['page_check']['infrastructure']['vm_explorer'], ui_worker_pid, prod_tail,
        soft_assert))

    pages_to_csv(pages, 'perf_ui_infra_vm_explorer.csv')
    pages_to_statistics_csv(pages, vm_infra_filters, 'ui-statistics.csv')


# Currently unskip 1129260 since a large environment is a requirement for this bug
@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1129260, unblock=True)])
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_resource_pools(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'resource_pools' in perf_tests['ui']['page_check']['infrastructure']:
        nav_limit = perf_tests['ui']['page_check']['infrastructure']['resource_pools']

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'infrastructure_resource_pools'), soft_assert))

    resource_pools = set([])
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'resource_pool/show')]"):
            resource_pools.add(sel.get_attribute(title, "title"))

    acc_bars = ['Properties', 'Relationships']

    pages.extend(navigate_quadicons(resource_pools, 'resource_pool',
        'infrastructure_resource_pools', nav_limit, ui_worker_pid, prod_tail, soft_assert,
        acc_bars))

    pages_to_csv(pages, 'perf_ui_infra_resource_pools.csv')
    pages_to_statistics_csv(pages, resource_pool_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_datastores(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    nav_limit = 0
    if 'datastores' in perf_tests['ui']['page_check']['infrastructure']:
        nav_limit = perf_tests['ui']['page_check']['infrastructure']['datastores']

    acc_bars = ['Properties', 'Relationships', 'Content']

    pages.extend(navigate_quadicons(get_all_datastores(), 'datastore', 'infrastructure_datastores',
        nav_limit, ui_worker_pid, prod_tail, soft_assert, acc_bars))

    pages_to_csv(pages, 'perf_ui_infra_datastores.csv')
    pages_to_statistics_csv(pages, storage_filters, 'ui-statistics.csv')


@pytest.mark.tier(3)
@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers", "cfme_log_level_rails_debug")
def test_perf_ui_infra_pxe(ui_worker_pid, soft_assert):
    pages, prod_tail = standup_perf_ui(ui_worker_pid, soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        'infrastructure_pxe'), soft_assert))

    pxe_acc = OrderedDict((('PXE Servers', 'pxe_servers'),
        ('Customization Templates', 'customization_templates'),
        ('System Image Types', 'system_image_types'), ('ISO Datastores', 'iso_datastores')))

    pages.extend(navigate_accordions(pxe_acc, 'infrastructure_pxe', (perf_tests['ui']['page_check']
        ['infrastructure']['pxe']), ui_worker_pid, prod_tail, soft_assert))

    pages_to_csv(pages, 'perf_ui_infra_pxe.csv')
    pages_to_statistics_csv(pages, infra_pxe_filters, 'ui-statistics.csv')
