# -*- coding: utf-8 -*
"""Functions and PageStat object for performance testing of the UI."""
from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.login import login_admin
from cfme.web_ui import accordion
from cfme.web_ui import listaccordion as list_acc
from cfme.web_ui import paginator
from cfme.web_ui import Quadicon
from utils.browser import browser
from utils.browser import ensure_browser_open
from utils.conf import perf_tests
from utils.log import logger
from utils.path import log_path
from utils.perf import generate_statistics
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
        if page.completedintime > perf_tests['ui']['threshold']['page_render']:
            soft_assert(False, 'Render Time Threshold ({} ms) exceeded: {}'.format(
                perf_tests['ui']['threshold']['page_render'], page))
            logger.warning('Slow Render, Slow Query(>%sms) Count: %s',
                perf_tests['ui']['threshold']['query_time'], len(page.slowselects))
            for slow in page.slowselects:
                logger.warning('Slow Query Log Line: %s', slow)
        if page.seleniumtime > perf_tests['ui']['threshold']['selenium']:
            soft_assert(False, 'Selenium Transaction Time Threshold ({} ms) exceeded: {}'.format(
                perf_tests['ui']['threshold']['selenium'], page))
            logger.warning('Slow Selenium Time')
        if page.selectcount > perf_tests['ui']['threshold']['query_count']:
            soft_assert(False, 'Query Count Threshold ({}) exceeded:    {}'.format(
                perf_tests['ui']['threshold']['query_count'], page))
        if page.uncachedcount > perf_tests['ui']['threshold']['uncached_count']:
            soft_assert(False, 'Uncached Query Count Threshold ({}) exceeded: {}'.format(
                perf_tests['ui']['threshold']['uncached_count'], page))
    return pages


def any_in(items, thing):
    return any(item in thing for item in items)


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

        logger.info('Starting to read tree: %s', acc_tree)
        tree_contents, sel_time = perf_bench_read_tree(accordion.tree(acc_tree))
        logger.info('%s tree read in %sms', acc_tree, sel_time)

        pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, False, None),
            soft_assert))

        nav_limit = 0
        count = -1
        if accordions[acc_tree] in ui_bench_pg_limit:
            nav_limit = ui_bench_pg_limit[accordions[acc_tree]]
            count = 0

        paths = []
        generate_tree_paths(tree_contents, [], paths)
        logger.info('Found %s tree paths', len(paths))
        for path in paths:
            logger.info('Navigating to: %s, %s', acc_tree, path[-1])
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
                logger.info('Could not navigate to: %s', path[-1])
            except UnexpectedAlertPresentException:
                logger.warning('UnexpectedAlertPresentException - page_name: %s, accordion: %s,'
                    ' path: %s', page_name, acc_tree, path[-1])
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
                                        logger.debug('DNN Skipping: %s', links[link].title)
                                    else:
                                        pages.extend(analyze_page_stat(perf_click(ui_worker_pid,
                                            prod_tail, True, links[link].click), soft_assert))

                        except NoSuchElementException:
                            logger.warning('NoSuchElementException - page_name:%s, Quadicon:%s,'
                                ' topbar:%s', page_name, q, topbar)
                            soft_assert(False, 'NoSuchElementException - page_name:{}, Quadicon:{},'
                                ' topbar:{}'.format(page_name, q, topbar))
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
    logger.info('Discovered %d Split Table items.', len(item_names))

    pages.extend(analyze_page_stat(perf_click(ui_worker_pid, prod_tail, True, sel.force_navigate,
        page_name), soft_assert))

    for item_name in item_names:
        logger.info('Navigating to Split Table Item: %s'. item_name)
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
            logger.error('Split Table Page was never found: page_name: %s, item: %s',
                page_name, item_name)
        # If nav_limit == 0 every item is navigated to
        if not nav_limit == 0 and count >= nav_limit:
            break

    return pages


def standup_perf_ui(ui_worker_pid, soft_assert):
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
                    if page.seleniumtime > 0:
                        pg_statistics.seleniumtimes.append(int(page.seleniumtime))
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
            if page.seleniumtime > 0:
                pg_statistics.seleniumtimes.append(int(page.seleniumtime))
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
        logger.info('Appending to: %s', report_file_name)
        outputfile = csvdata_path.open('a', ensure=True)
        appending = True
    else:
        logger.info('Writing to: %s', report_file_name)
        outputfile = csvdata_path.open('w', ensure=True)
        appending = False

    try:
        csvfile = csv.writer(outputfile)
        if not appending:
            metrics = ['samples', 'min', 'avg', 'median', 'max', 'std', '90', '99']
            measurements = ['sel_time', 'c_time', 'v_time', 'ar_time', 's_count', 'c_count',
                'uc_count']
            headers = ['pattern']
            for measurement in measurements:
                for metric in metrics:
                    headers.append('{}_{}'.format(measurement, metric))
            csvfile.writerow(headers)

        # Contents of CSV
        for page_statistics in all_statistics:
            if len(page_statistics.completedintimes) > 1:
                logger.debug('Samples/Avg/90th/Std: %s : %s : %s : %s Pattern: %s',
                    str(len(page_statistics.completedintimes)).rjust(7),
                    str(round(numpy.average(page_statistics.completedintimes), 2)).rjust(7),
                    str(round(numpy.percentile(page_statistics.completedintimes, 90), 2)).rjust(7),
                    str(round(numpy.std(page_statistics.completedintimes), 2)).rjust(7),
                    page_statistics.request)
            stats = [page_statistics.request]
            stats.extend(generate_statistics(page_statistics.seleniumtimes))
            stats.extend(generate_statistics(page_statistics.completedintimes))
            stats.extend(generate_statistics(page_statistics.viewstimes))
            stats.extend(generate_statistics(page_statistics.activerecordtimes))
            stats.extend(generate_statistics(page_statistics.selectcounts))
            stats.extend(generate_statistics(page_statistics.cachedcounts))
            stats.extend(generate_statistics(page_statistics.uncachedcounts))
            csvfile.writerow(stats)
    finally:
        outputfile.close()

    logger.debug('Size of Aggregated list of pages: %d', len(all_statistics))


def perf_bench_read_tree(tree):
    starttime = time()
    tree_contents = tree.read_contents()
    seleniumtime = int((time() - starttime) * 1000)
    return tree_contents, seleniumtime


def perf_click(uiworker_pid, tailer, measure_sel_time, clickable, *args):
    # Regular Expressions to find the ruby production completed time and select query time
    status_re = re.compile(r'Completed\s([0-9]*\s[a-zA-Z]*)\sin\s([0-9\.]*)ms')
    views_re = re.compile(r'Views:\s([0-9\.]*)ms')
    activerecord_re = re.compile(r'ActiveRecord:\s([0-9\.]*)ms')
    select_query_time_re = re.compile(r'\s\(([0-9\.]*)ms\)')
    worker_pid = '#' + uiworker_pid

    # Time the selenium transaction from "click"
    seleniumtime = 0
    if clickable:
        starttime = time()
        clickable(*args)
        seleniumtime = int((time() - starttime) * 1000)

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
                    if float(selecttime.group(1)) > perf_tests['ui']['threshold']['query_time']:
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
                views_result = views_re.search(line)
                if views_result:
                    pgstat.viewstime = float(views_result.group(1))
                activerecord_result = activerecord_re.search(line)
                if activerecord_result:
                    pgstat.activerecordtime = float(activerecord_result.group(1))
                pgstats.append(pgstat)
                pgstat = PageStat()
    if pgstats:
        if measure_sel_time:
            pgstats[-1].seleniumtime = seleniumtime
    timediff = time() - starttime
    logger.debug('Parsed (%s) lines in %s', line_count, timediff)
    return pgstats


class PageStat(object):
    """Object that represents page statistics and a list of any associated slow queries."""

    def __init__(self, request='', status='', seleniumtime=0, completedintime=0, viewstime=0,
            activerecordtime=0, selectcount=0, cachedcount=0, uncachedcount=0):
        self.headers = ['request', 'status', 'seleniumtime', 'completedintime', 'viewstime',
            'activerecordtime', 'selectcount', 'cachedcount', 'uncachedcount']
        self.request = request
        self.status = status
        self.seleniumtime = seleniumtime
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
        return 'Selenium/Completed/Views/ActiveRecord:' + str(self.seleniumtime).rjust(6) + \
            ':' + str(self.completedintime).rjust(8) + ':' + str(self.viewstime).rjust(8) + ':' + \
            str(self.activerecordtime).rjust(8) + ' Select/Cached/Uncached: ' + \
            str(self.selectcount).rjust(5) + ':' + str(self.cachedcount).rjust(5) + ':' \
            + str(self.uncachedcount).rjust(5) + ', Request: ' + self.request + \
            ', Status: ' + self.status


class PageStatLists(object):

    def __init__(self):
        self.request = ''
        self.seleniumtimes = []
        self.completedintimes = []
        self.viewstimes = []
        self.activerecordtimes = []
        self.selectcounts = []
        self.cachedcounts = []
        self.uncachedcounts = []
