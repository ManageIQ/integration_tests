# -*- coding: utf-8 -*
from cfme.cloud.provider import get_all_providers as get_all_cloud_provs
from cfme.cloud import instance
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import virtual_machines
from cfme.infrastructure.datastore import get_all_datastores
from cfme.infrastructure.host import get_all_hosts
from cfme.infrastructure.provider import get_all_providers
from cfme.login import login_admin
from cfme.web_ui import listaccordion as list_acc
from cfme.web_ui import paginator
from cfme.web_ui import Quadicon
from utils.browser import ensure_browser_open
from utils.conf import ui_bench_tests
from utils.log import logger
from utils.pagestats import PageStat
from utils.path import log_path
from utils.ssh import SSHTail
from selenium.common.exceptions import NoSuchElementException
from time import time
import csv
import pytest
import re


def analyze_page_stat(pages, soft_assert):
    for page in pages:
        logger.info(page)
        if page.completedintime > ui_bench_tests['threshold']['page_render']:
            soft_assert(False, 'Page Render Threshold ({} ms) exceeded: {}'.format(
                ui_bench_tests['threshold']['page_render'], page))
            logger.warning('Slow Page, Slow Query(>1s) Count: %d' % len(page.slowselects))
            for slow in page.slowselects:
                logger.warning('Slow Query Log Line: {}'.format(slow))
        if page.transactiontime > ui_bench_tests['threshold']['transaction']:
            soft_assert(False, 'Page Transaction Threshold ({} ms) exceeded: {}'.format(
                ui_bench_tests['threshold']['transaction'], page))
            logger.warning('Slow Page Transaction Time')
        if page.selectcount > ui_bench_tests['threshold']['query_count']:
            soft_assert(False, 'Query Cnt Threshold ({}) exceeded:    {}'.format(
                ui_bench_tests['threshold']['query_count'], page))
    return pages


def any_in(items, thing):
    return any(item in thing for item in items)


def navigate_every_quadicon(qnames, qtype, page_name, num_q_nav, ui_worker_pid, prod_tail,
        soft_assert, acc_topbars=[]):
    pages = []
    count = 0
    if num_q_nav == 0:
        count = -1
    assert len(qnames) > 0
    while (count < num_q_nav):
        for q in qnames:
            for page in paginator.pages():
                quadicon = Quadicon(str(q), qtype)
                if sel.is_displayed(quadicon):

                    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, sel.click,
                        quadicon), soft_assert))

                    for topbar in acc_topbars:
                        try:
                            if not list_acc.is_active(topbar):
                                list_acc.click(topbar)
                            links = list_acc.get_active_links(topbar)
                            for link in range(len(links)):
                                # Every click makes the previous list of links invalid
                                links = list_acc.get_active_links(topbar)
                                if link <= len(links):
                                    # Do not navigate to any link containing:
                                    dnn = ['parent', 'Capacity & Utilization', 'Timelines',
                                        'Show tree of all VMs by Resource Pool in this Cluster',
                                        'Show host drift history', 'Show VMs']
                                    if any_in(dnn, links[link].title):
                                        logger.debug('DNN Skipping: {}'.format(links[link].title))
                                    else:
                                        pages.extend(analyze_page_stat(perf_click(ui_worker_pid,
                                            prod_tail, links[link].click), soft_assert))

                        except NoSuchElementException:
                            logger.warning('NoSuchElementException - page_name:{}, Quadicon:{},'
                                ' topbar:{}, link title:{}'.format(page_name, q, topbar,
                                links[link].title))
                            soft_assert(False, 'NoSuchElementException - page_name:{}, Quadicon:{},'
                                ' topbar:{}, link title:{}'.format(page_name, q, topbar,
                                links[link].title))
                            break
                    count += 1
                    break

            pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, sel.force_navigate,
                page_name), soft_assert))

            if not num_q_nav == 0 and count == num_q_nav:
                break
    return pages


def navigate_tree_contents(tree_contents, path, paths):
    if type(tree_contents) is list:
        for item in tree_contents:
            navigate_tree_contents(item, path, paths)
    elif type(tree_contents) is tuple:
        path.append(tree_contents[0])
        navigate_tree_contents(tree_contents[1], path, paths)
        path.pop()
    else:
        path.append(tree_contents)
        paths.append(list(path))
        path.pop()


def standup_page_renders_n_queries(ssh_client):
    # Use evmserverd status to determine MiqUiWorker Pid (assuming 1 worker)
    exit_status, out = ssh_client.run_command('service evmserverd status 2> /dev/null | grep '
        '\'MiqUiWorker\' | awk \'{print $7}\'')
    assert exit_status == 0

    ui_worker_pid = str(out).strip()
    if out:
        logger.info('Obtained MiqUiWorker PID: {}'.format(ui_worker_pid))
    else:
        logger.error('Could not obtain MiqUiWorker PID, check evmserverd running...')
        assert out

    logger.info('Opening /var/www/miq/vmdb/log/production.log for tail')
    prod_tail = SSHTail('/var/www/miq/vmdb/log/production.log')
    prod_tail.set_initial_file_end()

    return ui_worker_pid, prod_tail


def pages_to_csv(pages, file_name):
    csvdata_path = log_path.join('csv_output', file_name)
    outputfile = csvdata_path.open('w', ensure=True)
    csvwriter = csv.DictWriter(outputfile, fieldnames=PageStat().headers, delimiter=',',
        quotechar='\'', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writeheader()
    for page in pages:
        csvwriter.writerow(dict(page))


def perf_click(uiworker_pid, tailer, clickable, *args):
    # Regular Expressions to find the ruby production completed time and select query time
    status_re = re.compile(r'Completed\s([0-9]*\s[a-zA-Z]*)\sin\s([0-9\.]*)ms')
    select_query_time_re = re.compile(r'\s\(([0-9\.]*)ms\)')
    worker_pid = '#' + uiworker_pid

    # Time the UI transaction from "click"
    transactiontime = 0
    if clickable:
        starttime = time()
        clickable(*args)
        transactiontime = int((time() - starttime) * 1000)

    pgstats = []
    pgstat = PageStat()
    line_count = 0
    starttime = time()

    for line in tailer:
        line_count += 1
        if worker_pid in line:
            if 'SELECT' in line:
                pgstat.selectcount += 1
                selecttime = select_query_time_re.search(line)
                if selecttime:
                    if float(selecttime.group(1)) > ui_bench_tests['threshold']['query_time']:
                        pgstat.slowselects.append(line)
            if 'CACHE' in line:
                pgstat.cachecount += 1
            if 'INFO -- : Started' in line:
                # Obtain method and requested page
                started_idx = line.index('Started') + 8
                pgstat.request = line[started_idx:line.index('for', 72)]
            if 'INFO -- : Completed' in line:
                # Obtain status code and total render time
                status_result = status_re.search(line)
                if status_result:
                    pgstat.status = status_result.group(1)
                    pgstat.completedintime = float(status_result.group(2))

                # Redirects don't always have a view timing
                try:
                    vanchor = line.index('Views') + 7
                    pgstat.viewstime = line[vanchor:line.index('ms', vanchor)]
                except:
                    pass
                try:
                    aranchor = line.index('ActiveRecord') + 14
                    pgstat.activerecordtime = line[aranchor:line.index('ms', aranchor)]
                except:
                    pass
                pgstats.append(pgstat)
                pgstat = PageStat()
    if pgstats:
        pgstats[-1].transactiontime = transactiontime
    timediff = time() - starttime
    logger.debug('Parsed ({}) lines in {}'.format(line_count, timediff))
    return pgstats


@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers")
def test_ems_cloud_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_ems_cloud_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_ems_cloud_check'] = 0

    pages = navigate_every_quadicon(get_all_cloud_provs(), 'cloud_prov', 'clouds_providers',
        ui_bench_tests['page_check']['num_ems_cloud_check'], ui_worker_pid, prod_tail, soft_assert)

    pages_to_csv(pages, 'page_renders_n_queries_ems_cloud.csv')


@pytest.mark.perf_ui_cloud
@pytest.mark.usefixtures("setup_cloud_providers")
def test_vm_cloud_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_vm_cloud_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_vm_cloud_check'] = 0

    ensure_browser_open()
    pages = analyze_page_stat(perf_click(ui_worker_pid, prod_tail, login_admin), soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, sel.force_navigate,
        'clouds_instances'), soft_assert))

    # Read the tree in by expanding each folder
    logger.info('Starting to read the tree...')
    tree_contents = instance.visible_tree.read_contents()
    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, None), soft_assert))

    logger.info('Creating Navigation path to every Instance...')
    vmpaths = []
    navigate_tree_contents(tree_contents, [], vmpaths)

    logger.info('Found {} Instances'.format(len(vmpaths)))
    count = 0
    for vm in vmpaths:
        logger.info('Navigating to Instance: {}'.format(vm[-1]))
        try:
            pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail,
                virtual_machines.visible_tree.click_path, *vm), soft_assert))
            count += 1
            # Navigate out of the vm cloud page every 4th vm
            if (count % 4) == 3:
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail,
                    sel.force_navigate, 'dashboard'), soft_assert))
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail,
                    sel.force_navigate, 'clouds_instances'), soft_assert))
        except CandidateNotFound:
            logger.info('Could not navigate to: '.format(vm[-1]))

        if count >= ui_bench_tests['page_check']['num_vm_cloud_check']:
            break

    pages_to_csv(pages, 'page_renders_n_queries_vm_cloud.csv')


@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_ems_infra_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_ems_infra_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_ems_infra_check'] = 0

    pages = navigate_every_quadicon(get_all_providers(), 'infra_prov', 'infrastructure_providers',
        ui_bench_tests['page_check']['num_ems_infra_check'], ui_worker_pid, prod_tail, soft_assert)

    pages_to_csv(pages, 'page_renders_n_queries_ems_infra.csv')


@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_ems_cluster_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_ems_cluster_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_ems_cluster_check'] = 0

    pages = []

    ensure_browser_open()
    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, login_admin), soft_assert))

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, sel.force_navigate,
        'infrastructure_clusters'), soft_assert))

    clusters = set([])
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'ems_cluster/show')]"):
            clusters.add(sel.get_attribute(title, "title"))

    acc_bars = ['Properties', 'Relationships']

    pages.extend(navigate_every_quadicon(clusters, 'cluster', 'infrastructure_clusters',
        ui_bench_tests['page_check']['num_ems_cluster_check'], ui_worker_pid, prod_tail,
        soft_assert, acc_bars))

    pages_to_csv(pages, 'page_renders_n_queries_ems_clusters.csv')


@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_host_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_host_infra_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_host_infra_check'] = 0

    acc_bars = ['Properties', 'Relationships', 'Security', 'Configuration']

    pages = navigate_every_quadicon(get_all_hosts(), 'host', 'infrastructure_hosts',
        ui_bench_tests['page_check']['num_host_infra_check'], ui_worker_pid, prod_tail, soft_assert,
        acc_bars)

    pages_to_csv(pages, 'page_renders_n_queries_host_infra.csv')


@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_vm_infra_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    ensure_browser_open()
    pages = analyze_page_stat(perf_click(ui_worker_pid, prod_tail, login_admin), soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, sel.force_navigate,
        'infrastructure_virtual_machines'), soft_assert))

    # Read the infrastructure tree in by expanding each folder
    logger.info('Starting to read the tree...')
    tree_contents = virtual_machines.visible_tree.read_contents()
    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, None), soft_assert))

    logger.info('Creating Navigation path to every VM/Template...')
    vmpaths = []
    navigate_tree_contents(tree_contents, [], vmpaths)

    logger.info('Found {} VMs/Templates'.format(len(vmpaths)))
    count = 0
    for vm in vmpaths:
        logger.info('Navigating to VM/Template: {}'.format(vm[-1]))
        try:
            pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail,
                virtual_machines.visible_tree.click_path, *vm), soft_assert))
            count += 1
            # Navigate out of the vm infrastructure page every 4th vm
            if (count % 4) == 3:
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail,
                    sel.force_navigate, 'dashboard'), soft_assert))
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail,
                    sel.force_navigate, 'infrastructure_virtual_machines'), soft_assert))
        except CandidateNotFound:
            logger.info('Could not navigate to: '.format(vm[-1]))

        if count >= ui_bench_tests['page_check']['num_vm_infra_check']:
            break

    pages_to_csv(pages, 'page_renders_n_queries_vm_infra.csv')


@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_resource_pool_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_ems_resource_pool_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_ems_resource_pool_check'] = 0

    ensure_browser_open()
    pages = analyze_page_stat(perf_click(ui_worker_pid, prod_tail, login_admin), soft_assert)

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, sel.force_navigate,
        'infrastructure_resource_pools'), soft_assert))

    resource_pools = set([])
    for page in paginator.pages():
        for title in sel.elements("//div[@id='quadicon']/../../../tr/td/a[contains(@href,"
                "'resource_pool/show')]"):
            resource_pools.add(sel.get_attribute(title, "title"))

    acc_bars = ['Properties', 'Relationships']

    pages.extend(navigate_every_quadicon(resource_pools, 'resource_pool',
        'infrastructure_resource_pools',
        ui_bench_tests['page_check']['num_ems_resource_pool_check'], ui_worker_pid, prod_tail,
        soft_assert, acc_bars))

    pages_to_csv(pages, 'page_renders_n_queries_resource_pool.csv')


@pytest.mark.perf_ui_infrastructure
@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_storage_render_times_n_queries(ssh_client, soft_assert):
    ui_worker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    if 'num_storage_check' not in ui_bench_tests['page_check']:
        ui_bench_tests['page_check']['num_storage_check'] = 0

    acc_bars = ['Properties', 'Relationships', 'Content']

    pages = navigate_every_quadicon(get_all_datastores(), 'datastore', 'infrastructure_datastores',
        ui_bench_tests['page_check']['num_storage_check'], ui_worker_pid, prod_tail, soft_assert,
        acc_bars)

    pages_to_csv(pages, 'page_renders_n_queries_storage.csv')
