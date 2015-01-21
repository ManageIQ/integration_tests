# -*- coding: utf-8 -*
"""Set of functions and PageStat object for performance testing of the UI.
"""
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.login import login_admin
from utils.browser import ensure_browser_open
from cfme.web_ui import accordion
from cfme.web_ui import listaccordion as list_acc
from cfme.web_ui import paginator
from cfme.web_ui import Quadicon
from utils.browser import browser
from utils.conf import ui_bench_tests
from utils.log import logger
from utils.path import log_path
from utils.ssh import SSHTail
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import UnexpectedAlertPresentException
from time import time
import csv
import numpy
import re


def analyze_page_stat(pages, soft_assert):
    for page in pages:
        logger.info(page)
        if page.completedintime > ui_bench_tests['threshold']['page_render']:
            soft_assert(False, 'Render Time Threshold ({} ms) exceeded: {}'.format(
                ui_bench_tests['threshold']['page_render'], page))
            logger.warning('Slow Render, Slow Query(>{}ms) Count: {}'.format(
                ui_bench_tests['threshold']['query_time'], len(page.slowselects)))
            for slow in page.slowselects:
                logger.warning('Slow Query Log Line: {}'.format(slow))
        if page.transactiontime > ui_bench_tests['threshold']['transaction']:
            soft_assert(False, 'Transaction Time Threshold ({} ms) exceeded: {}'.format(
                ui_bench_tests['threshold']['transaction'], page))
            logger.warning('Slow Page Transaction Time')
        if page.selectcount > ui_bench_tests['threshold']['query_count']:
            soft_assert(False, 'Query Count Threshold ({}) exceeded:    {}'.format(
                ui_bench_tests['threshold']['query_count'], page))
        if page.uncachedcount > ui_bench_tests['threshold']['uncached_count']:
            soft_assert(False, 'Uncached Query Count Threshold ({}) exceeded: {}'.format(
                ui_bench_tests['threshold']['uncached_count'], page))
    return pages


def any_in(items, thing):
    return any(item in thing for item in items)


def generate_statistics(the_list):
    if len(the_list) == 0:
        return '0,0,0,0,0,0'
    else:
        return '{},{},{},{},{},{}'.format(len(the_list), numpy.amin(the_list), numpy.amax(the_list),
            round(numpy.average(the_list), 2), round(numpy.std(the_list), 2),
            numpy.percentile(the_list, 90))


def generate_tree_paths(tree_contents, path, paths):
    if type(tree_contents) is list:
        for item in tree_contents:
            generate_tree_paths(item, path, paths)
    elif type(tree_contents) is tuple:
        path.append(tree_contents[0])
        generate_tree_paths(tree_contents[1], path, paths)
        path.pop()
    else:
        path.append(tree_contents)
        paths.append(list(path))
        path.pop()


def navigate_accordions(accordions, page_name, ui_bench_pg_limit, ui_worker_pid, prod_tail,
        soft_assert):
    pages = []
    for acc_tree in accordions:
        pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, accordion.click,
            acc_tree), soft_assert))

        logger.info('Starting to read tree: {}'.format(acc_tree))
        tree_contents, t_time = perf_bench_read_tree(accordion.tree(acc_tree))
        logger.info('{} tree read in {}ms'.format(acc_tree, t_time))

        pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, False, None),
            soft_assert))

        nav_limit = 0
        count = -1
        if accordions[acc_tree] in ui_bench_pg_limit:
            nav_limit = ui_bench_pg_limit[accordions[acc_tree]]
            count = 0

        paths = []
        generate_tree_paths(tree_contents, [], paths)
        logger.info('Found {} tree paths'.format(len(paths)))
        for path in paths:
            logger.info('Navigating to: {}, {}'.format(acc_tree, path[-1]))
            try:
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True,
                    accordion.tree(acc_tree).click_path, *path), soft_assert))
                count += 1
                # Navigate out of the page every 4th click
                if (count % 4) == 0:
                    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, False,
                        sel.force_navigate, 'dashboard'), soft_assert))
                    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, False,
                        sel.force_navigate, page_name), soft_assert))
            except CandidateNotFound:
                logger.info('Could not navigate to: '.format(path[-1]))
            except UnexpectedAlertPresentException:
                logger.warning('UnexpectedAlertPresentException - page_name: {}, accordion: {},'
                    ' path: {}'.format(page_name, acc_tree, path[-1]))
                browser().switch_to_alert().dismiss()
            if not nav_limit == 0 and count >= nav_limit:
                break
    return pages


def navigate_quadicons(q_names, q_type, page_name, nav_limit, ui_worker_pid, prod_tail, soft_assert,
        acc_topbars=[]):
    pages = []
    count = 0
    if nav_limit == 0:
        count = -1
    assert len(q_names) > 0
    while (count < nav_limit):
        for q in q_names:
            for page in paginator.pages():
                quadicon = Quadicon(str(q), q_type)
                if sel.is_displayed(quadicon):

                    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True,
                        sel.click, quadicon), soft_assert))

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
                                            prod_tail, True, links[link].click), soft_assert))

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

            pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True,
                sel.force_navigate, page_name), soft_assert))
            # If nav_limit == 0 , every item is navigated to
            if not nav_limit == 0 and count == nav_limit:
                break

    return pages


def navigate_split_table(table, page_name, nav_limit, ui_worker_pid, prod_tail, soft_assert):
    pages = []
    count = 0
    if nav_limit == 0:
        count = -1

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, False, sel.force_navigate,
        page_name), soft_assert))
    # Obtain all items from Split Table
    item_names = []
    for page in paginator.pages():
        rows = table.rows()
        for row in rows:
            item_names.append(row.columns[2].text)
    logger.info('Discovered {} Split Table items.'.format(len(item_names)))

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        page_name), soft_assert))

    for item_name in item_names:
        logger.info('Navigating to Split Table Item: {}'.format(item_name))
        page_found = False
        for page in paginator.pages():
            cell_found = table.find_cell('name', item_name)
            if cell_found:
                page_found = True
                count += 1
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True,
                    table.click_cell, 'name', item_name), soft_assert))
                pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True,
                    sel.force_navigate, page_name), soft_assert))
                break
        if not page_found:
            logger.error('Split Table Page was never found: page_name: {}, item: {}'.format(
                page_name, item_name))
        # If nav_limit == 0 every item is navigated to
        if not nav_limit == 0 and count >= nav_limit:
            break

    return pages


def standup_perf_ui(ui_worker_pid, ssh_client, soft_assert):
    logger.info('Opening /var/www/miq/vmdb/log/production.log for tail')
    prod_tail = SSHTail('/var/www/miq/vmdb/log/production.log')
    prod_tail.set_initial_file_end()

    ensure_browser_open()
    pages = analyze_page_stat(perf_click(ui_worker_pid, prod_tail, False, login_admin), soft_assert)

    return pages, prod_tail


def pages_to_csv(pages, file_name):
    csvdata_path = log_path.join('csv_output', file_name)
    outputfile = csvdata_path.open('w', ensure=True)
    csvwriter = csv.DictWriter(outputfile, fieldnames=PageStat().headers, delimiter=',',
        quotechar='\'', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writeheader()
    for page in pages:
        csvwriter.writerow(dict(page))


def pages_to_statistics_csv(pages, filters, report_file_name):
    all_statistics = []
    for page in pages:
        # Determine if the page matches a pattern and swap request to pattern
        for p_filter in filters:
            results = p_filter.search(page.request.strip())
            if results:
                page.request = p_filter.pattern
                break
        added = False

        if len(all_statistics) > 0:
            for pg_statistics in all_statistics:
                if pg_statistics.request == page.request:
                    if page.transactiontime > 0:
                        pg_statistics.transactiontimes.append(int(page.transactiontime))
                    pg_statistics.completedintimes.append(float(page.completedintime))
                    if page.viewstime > 0:
                        pg_statistics.viewstimes.append(float(page.viewstime))
                    pg_statistics.activerecordtimes.append(float(page.activerecordtime))
                    pg_statistics.selectcounts.append(int(page.selectcount))
                    pg_statistics.cachedcounts.append(int(page.cachedcount))
                    pg_statistics.uncachedcounts.append(int(page.uncachedcount))
                    added = True
                    break

        if not added:
            pg_statistics = PageStatLists()
            pg_statistics.request = page.request
            if page.transactiontime > 0:
                pg_statistics.transactiontimes.append(int(page.transactiontime))
            pg_statistics.completedintimes.append(float(page.completedintime))
            if page.viewstime > 0:
                pg_statistics.viewstimes.append(float(page.viewstime))
            pg_statistics.activerecordtimes.append(float(page.activerecordtime))
            pg_statistics.selectcounts.append(int(page.selectcount))
            pg_statistics.cachedcounts.append(int(page.cachedcount))
            pg_statistics.uncachedcounts.append(int(page.uncachedcount))
            all_statistics.append(pg_statistics)

    csvdata_path = log_path.join('csv_output', report_file_name)
    if csvdata_path.isfile():
        logger.info('Appending to: {}'.format(report_file_name))
        outputfile = csvdata_path.open('a', ensure=True)
    else:
        logger.info('Writing to: {}'.format(report_file_name))
        outputfile = csvdata_path.open('w', ensure=True)
        outputfile.write('pattern,t_time_samples,t_time_min,t_time_max,t_time_avg,t_time_std'
            ',t_time_90,c_time_samples,c_time_min,c_time_max,c_time_avg,c_time_std,c_time_90'
            ',v_time_samples,v_time_min,v_time_max,v_time_avg,v_time_std,v_time_90'
            ',ar_time_samples,ar_time_min,ar_time_max,ar_time_avg,ar_time_std,ar_time_90'
            ',s_count_samples,s_count_min,s_count_max,s_count_avg,s_count_std,s_count_90'
            ',c_count_samples,c_count_min,c_count_max,c_count_avg,c_count_std,c_count_90'
            ',uc_count_samples,uc_count_min,uc_count_max,uc_count_avg,uc_count_std,uc_count_90\n')

    # Contents of CSV
    for page_statistics in all_statistics:
        if len(page_statistics.completedintimes) > 1:
            logger.debug('Samples/Avg/90th/Std: {} : {} : {} : {} Pattern: {}'.format(
                str(len(page_statistics.completedintimes)).rjust(7),
                str(round(numpy.average(page_statistics.completedintimes), 2)).rjust(7),
                str(round(numpy.percentile(page_statistics.completedintimes, 90), 2)).rjust(7),
                str(round(numpy.std(page_statistics.completedintimes), 2)).rjust(7),
                page_statistics.request))
        stats = '{},{},{},{},{},{},{},{}\n'.format(page_statistics.request,
            generate_statistics(numpy.array(page_statistics.transactiontimes)),
            generate_statistics(numpy.array(page_statistics.completedintimes)),
            generate_statistics(numpy.array(page_statistics.viewstimes)),
            generate_statistics(numpy.array(page_statistics.activerecordtimes)),
            generate_statistics(numpy.array(page_statistics.selectcounts)),
            generate_statistics(numpy.array(page_statistics.cachedcounts)),
            generate_statistics(numpy.array(page_statistics.uncachedcounts)))
        outputfile.write(stats)
    outputfile.close()

    logger.debug('Size of Aggregated list of pages: {}'.format(len(all_statistics)))


def perf_bench_read_tree(tree):
    starttime = time()
    tree_contents = tree.read_contents()
    transactiontime = int((time() - starttime) * 1000)
    return tree_contents, transactiontime


def perf_click(uiworker_pid, tailer, measure_t_time, clickable, *args):
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
                pgstat.cachedcount += 1
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

                pgstat.uncachedcount = pgstat.selectcount - pgstat.cachedcount

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
        if measure_t_time:
            pgstats[-1].transactiontime = transactiontime
    timediff = time() - starttime
    logger.debug('Parsed ({}) lines in {}'.format(line_count, timediff))
    return pgstats


"""Object that represents page statistics and a list of any associated slow queries.
"""


class PageStat(object):

    def __init__(self, request='', status='', transactiontime=0, completedintime=0, viewstime=0,
            activerecordtime=0, selectcount=0, cachedcount=0, uncachedcount=0):
        self.headers = ['request', 'status', 'transactiontime', 'completedintime', 'viewstime',
            'activerecordtime', 'selectcount', 'cachedcount', 'uncachedcount']
        self.request = request
        self.status = status
        self.transactiontime = transactiontime
        self.completedintime = completedintime
        self.viewstime = viewstime
        self.activerecordtime = activerecordtime
        self.selectcount = selectcount
        self.cachedcount = cachedcount
        self.uncachedcount = uncachedcount
        self.slowselects = []

    def __iter__(self):
        for header in self.headers:
            yield header, getattr(self, header)

    def __str__(self):
        return 'Transaction/Completed/Views/ActiveRecord:' + str(self.transactiontime).rjust(6) + \
            ':' + str(self.completedintime).rjust(8) + ':' + str(self.viewstime).rjust(8) + ':' + \
            str(self.activerecordtime).rjust(8) + ' Select/Cached/Uncached: ' + \
            str(self.selectcount).rjust(5) + ':' + str(self.cachedcount).rjust(5) + ':' \
            + str(self.uncachedcount).rjust(5) + ', Request: ' + self.request + \
            ', Status: ' + self.status


class PageStatLists(object):

    def __init__(self):
        self.request = ''
        self.transactiontimes = []
        self.completedintimes = []
        self.viewstimes = []
        self.activerecordtimes = []
        self.selectcounts = []
        self.cachedcounts = []
        self.uncachedcounts = []
