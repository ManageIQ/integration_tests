# -*- coding: utf-8 -*
from cfme.infrastructure import virtual_machines
from cfme.infrastructure.datastore import get_all_datastores
from cfme.infrastructure.host import get_all_hosts
from cfme.infrastructure.provider import get_all_providers
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import listaccordion as list_acc
from cfme.web_ui import paginator
from cfme.web_ui import Quadicon
from utils.conf import ui_bench_tests
from utils.log import logger
from utils.pagestats import PageStat
from utils.path import log_path
from utils.ssh import SSHTail
from selenium.common.exceptions import NoSuchElementException
import csv
import datetime
import re


def analyze_page_stat(pages, soft_assert):
    for page in pages:
        logger.info(page)
        if page.completedin > ui_bench_tests['page_render_threshold']:
            soft_assert(False, 'Page Render Threshold ({} ms) exceeded: {}'.format(
                ui_bench_tests['page_render_threshold'], page))
            logger.warning('Slow Page, Slow Query(>1s) Count: %d' % len(page.slowselects))
            for slow in page.slowselects:
                logger.warning('Slow Query Log Line: ' + slow)
        if page.selectcount > ui_bench_tests['query_count_threshold']:
            soft_assert(False, 'Query Cnt Threshold ({}) exceeded:    {}'.format(
                ui_bench_tests['query_count_threshold'], page))
    return pages


def navigate_every_quadicon(qnames, qtype, num_repeat, page_name, soft_assert, acc_topbars=[]):
    for i in range(num_repeat):
        for q in qnames:
            for page in paginator.pages():
                quadicon = Quadicon(str(q), qtype)
                if sel.is_displayed(quadicon):
                    sel.click(quadicon)
                    for topbar in acc_topbars:
                        try:
                            links = list_acc.get_active_links(topbar)
                            if not list_acc.is_active(topbar):
                                list_acc.click(topbar)
                            for link in range(len(links)):
                                # Every click makes the previous list of links invalid
                                links = list_acc.get_active_links(topbar)
                                if link <= len(links):
                                    if not 'parent' in links[link].title:
                                        links[link].click()
                        except NoSuchElementException:
                            logger.warning('NoSuchElementException - page_name:{}, Quadicon:{},'
                                ' topbar:{}, link title:{}'.format(page_name, q, topbar,
                                links[link].title))
                            soft_assert(False, 'NoSuchElementException - page_name:{}, Quadicon:{},'
                                ' topbar:{}, link title:{}'.format(page_name, q, topbar,
                                links[link].title))
                            break
                    break
            sel.force_navigate(page_name)


def navigate_tree_vms(tree_contents, path, paths):
    if type(tree_contents) is list:
        for item in tree_contents:
            navigate_tree_vms(item, path, paths)
    elif type(tree_contents) is tuple:
        path.append(tree_contents[0])
        navigate_tree_vms(tree_contents[1], path, paths)
        path.pop()
    else:
        path.append(tree_contents)
        paths.append(list(path))
        path.pop()


def standup_page_renders_n_queries(ssh_client):
    # Use evmserverd status to determine MiqUiWorker Pid (assuming 1 worker)
    exit_status, out = ssh_client.run_command('service evmserverd status | grep \'MiqUiWorker\'' +
        ' | awk \'{print $7}\'')
    assert exit_status == 0

    miq_uiworker_pid = str(out).strip()
    if out:
        logger.info('Obtained MiqUiWorker PID: {}'.format(miq_uiworker_pid))
    else:
        logger.error('Could not obtain MiqUiWorker PID, check evmserverd running...')
        assert out

    logger.info('Opening /var/www/miq/vmdb/log/production.log for tail')
    prod_tail = SSHTail('/var/www/miq/vmdb/log/production.log')
    prod_tail.set_initial_file_end()

    return miq_uiworker_pid, prod_tail


def pages_to_csv(pages, file_name):
    csvdata_path = log_path.join('csv_output', file_name)
    outputfile = csvdata_path.open('w', ensure=True)
    csvwriter = csv.DictWriter(outputfile, fieldnames=PageStat().headers, delimiter=',',
        quotechar='\'', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writeheader()
    for page in pages:
        csvwriter.writerow(dict(page))


def parse_production_log(miq_uiworker_pid, tailer):
    # Regular Expressions to find the ruby production completed time and select query time
    status_re = re.compile(r'Completed\s([0-9]*\s[a-zA-Z]*)\sin\s([0-9]*)ms')
    select_query_time_re = re.compile(r'\s\(([0-9\.]*)ms\)')
    worker_pid = '#' + miq_uiworker_pid

    pgstats = []
    pgstat = PageStat()
    line_count = 0
    starttime = datetime.datetime.utcnow()

    for line in tailer:
        line_count += 1
        if worker_pid in line:
            if 'SELECT' in line:
                pgstat.selectcount += 1
                selecttime = select_query_time_re.search(line)
                if selecttime:
                    if float(selecttime.group(1)) > ui_bench_tests['query_time_threshold']:
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
                    pgstat.completedin = int(status_result.group(2))

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

    endtime = datetime.datetime.utcnow()
    timediff = endtime - starttime
    logger.info('Parsed ({}) lines in {}'.format(line_count, timediff))
    return pgstats


def test_ems_infra_render_times_n_queries(ssh_client, soft_assert):
    miq_uiworker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    navigate_every_quadicon(get_all_providers(), 'infra_prov',
        ui_bench_tests['num_repeat_provider'], 'infrastructure_providers', soft_assert)

    pages = analyze_page_stat(parse_production_log(miq_uiworker_pid, prod_tail), soft_assert)

    pages_to_csv(pages, 'page_renders_n_queries_ems_infra.csv')


def test_host_render_times_n_queries(ssh_client, soft_assert):
    miq_uiworker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    acc_bars = ['Properties', 'Relationships', 'Security', 'Configuration']

    navigate_every_quadicon(get_all_hosts(), 'host', ui_bench_tests['num_repeat_host'],
        'infrastructure_hosts', soft_assert, acc_bars)

    pages = analyze_page_stat(parse_production_log(miq_uiworker_pid, prod_tail), soft_assert)

    pages_to_csv(pages, 'page_renders_n_queries_host_infra.csv')


def test_vm_infra_render_times_n_queries(ssh_client, soft_assert):
    miq_uiworker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    sel.force_navigate('infrastructure_virtual_machines')
    pages = analyze_page_stat(parse_production_log(miq_uiworker_pid, prod_tail), soft_assert)

    # Read the infrastructure tree in by expanding each folder
    logger.info('Starting to read the tree...')
    tree_contents = virtual_machines.visible_tree.read_contents()
    pages.extend(analyze_page_stat(parse_production_log(miq_uiworker_pid, prod_tail), soft_assert))

    logger.info('Creating Navigation path to every VM/Template...')
    vmpaths = []
    navigate_tree_vms(tree_contents, [], vmpaths)

    logger.info('Found {} VMs/Templates'.format(len(vmpaths)))
    count = 0
    for vm in vmpaths:
        logger.info('Navigating to VM/Template: {}'.format(vm[-1]))
        try:
            virtual_machines.visible_tree.click_path(*vm)
            pages.extend(analyze_page_stat(parse_production_log(miq_uiworker_pid, prod_tail),
                soft_assert))
            count += 1
            # Navigate out of the vm infrastructure page every 4th vm
            if (count % 4) == 3:
                sel.force_navigate('dashboard')
                sel.force_navigate('infrastructure_virtual_machines')
        except CandidateNotFound:
            logger.info('Could not navigate to: '.format(vm[-1]))

        if count >= ui_bench_tests['num_vm_check']:
            break

    pages_to_csv(pages, 'page_renders_n_queries_vm_infra.csv')


def test_storage_render_times_n_queries(ssh_client, soft_assert):
    miq_uiworker_pid, prod_tail = standup_page_renders_n_queries(ssh_client)

    acc_bars = ['Properties', 'Relationships', 'Content']

    navigate_every_quadicon(get_all_datastores(), 'datastore',
        ui_bench_tests['num_repeat_datastore'], 'infrastructure_datastores', soft_assert, acc_bars)

    pages = analyze_page_stat(parse_production_log(miq_uiworker_pid, prod_tail), soft_assert)

    pages_to_csv(pages, 'page_renders_n_queries_storage.csv')
