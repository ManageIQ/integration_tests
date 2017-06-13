# -*- coding: utf-8 -*-
import re

import pytest

from cfme.containers.provider import ContainersProvider
from cfme.intelligence.reports.reports import CannedSavedReport, CustomReport, select
from utils import testgen
from utils.blockers import BZ
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.meta(
        server_roles='+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.fixture(scope='module')
def node_hardwares_db_data(appliance):

    """Grabbing hardwares table data for nodes"""

    db = appliance.db
    hardwares_table = db['hardwares']
    container_nodes = db['container_nodes']

    out = {}
    for node in db.session.query(container_nodes).all():

        out[node.name] = hardwares_table.__table__.select().where(
            hardwares_table.id == node.id
        ).execute().fetchone()

    return out


@pytest.fixture(scope='function')
def pods_per_ready_status(provider):
    """Grabing the pods and their ready status from API"""
    #  TODO: Add later this logic to wrapanapi
    entities_j = provider.mgmt.api.get('pod')[1]['items']
    out = {}
    for entity_j in entities_j:
        out[entity_j['metadata']['name']] = next(
            (True if condition['status'].lower() == 'true' else False)
            for condition in entity_j['status']['conditions']
            if condition['type'].lower() == 'ready'
        )

    return out


def get_vpor_data_by_name(vporizer_, name):
    return [vals for vals in vporizer_ if vals.resource_name == name]


def get_report(menu_name):
    """Queue a report by menu name , wait for finish and return it"""
    path_to_report = ['Configuration Management', 'Containers', menu_name]
    run_at = CannedSavedReport.queue_canned_report(path_to_report)
    return CannedSavedReport(path_to_report, run_at)


@pytest.mark.polarion('CMP-10617')
def test_container_reports_base_on_options(soft_assert):
    navigate_to(CustomReport, 'New')
    for base_on in (
        'Chargeback Container Images',
        'Container Images',
        'Container Services',
        'Container Templates',
        'Containers',
        re.compile('Performance - Container\s*Nodes'),
        re.compile('Performance - Container\s*Projects'),
        'Performance - Containers'
    ):
        compare = (base_on.match if hasattr(base_on, 'match') else base_on.__eq__)
        option = [opt for opt in select(id="chosen_model").all_options
                  if compare(str(opt.text))]
        soft_assert(option, 'Could not find option "{}" for base report on.'.format(base_on))


@pytest.mark.meta(blockers=[BZ(1435958, forced_streams=["5.8"])])
@pytest.mark.polarion('CMP-9533')
def test_pods_per_ready_status(soft_assert, pods_per_ready_status):

    report = get_report('Pods per Ready Status')
    for row in report.data.rows:
        name = row['# Pods per Ready Status']
        readiness_ui = (True if row['Ready Condition Status'].lower() == 'true'
                        else False)
        if soft_assert(name in pods_per_ready_status,  # this check based on BZ#1435958
                'Could not find pod "{}" in openshift.'
                .format(name)):
            soft_assert(pods_per_ready_status[name] == readiness_ui,
                        'For pod "{}" expected readiness is "{}" got "{}"'
                        .format(name, pods_per_ready_status[name], readiness_ui))


@pytest.mark.polarion('CMP-9536')
def test_report_nodes_by_capacity(appliance, soft_assert, node_hardwares_db_data):

    report = get_report('Nodes By Capacity')
    for row in report.data.rows:

        hw = node_hardwares_db_data[row['Name']]

        soft_assert(hw.cpu_total_cores == int(row['CPU Cores']),
                    'Number of CPU cores is wrong: expected {}'
                    ' got {}'.format(hw.cpu_total_cores, row['CPU Cores']))

        # The following block is to convert whatever we have to MB
        memory_ui = float(re.sub(r'[a-zA-Z,]', '', row['Memory']))
        if 'gb' in row['Memory'].lower():
            memory_mb_ui = memory_ui * 1024
            # Shift hw.memory_mb to GB, round to the number of decimals of memory_mb_db
            # and shift back to MB:
            memory_mb_db = round(hw.memory_mb / 1024.0,
                                 len(str(memory_mb_ui).split('.')[1])) * 1024
        else:  # Assume it's MB
            memory_mb_ui = memory_ui
            memory_mb_db = hw.memory_mb

        soft_assert(memory_mb_ui == memory_mb_db,
                    'Memory (MB) is wrong for node "{}": expected {} got {}'
                    .format(row['Name'], memory_mb_ui, memory_mb_db))


@pytest.mark.polarion('CMP-10034')
def test_report_nodes_by_cpu_usage(appliance, soft_assert, vporizer):

    report = get_report('Nodes By CPU Usage')
    for row in report.data.rows:

        vpor_values = get_vpor_data_by_name(vporizer, row["Name"])[0]
        usage_db = round(vpor_values.max_cpu_usage_rate_average, 2)
        usage_report = round(float(row['CPU Usage (%)']), 2)

        soft_assert(usage_db == usage_report,
                    'CPU usage is wrong for node "{}": expected {} got {}'
                    .format(row['Name'], usage_db, usage_report))


@pytest.mark.polarion('CMP-10033')
def test_report_nodes_by_memory_usage(appliance, soft_assert, vporizer):

    report = get_report('Nodes By Memory Usage')
    for row in report.data.rows:

        vpor_values = get_vpor_data_by_name(vporizer, row["Name"])[0]
        usage_db = round(vpor_values.max_mem_usage_absolute_average, 2)
        usage_report = round(float(row['Memory Usage (%)']), 2)

        soft_assert(usage_db == usage_report,
                    'CPU usage is wrong for node "{}": expected {} got {}.'
                    .format(row['Name'], usage_db, usage_report))


@pytest.mark.meta(blockers=[BZ(1436698, forced_streams=["5.6", "5.7"])])
@pytest.mark.polarion('CMP-10033')
def test_report_nodes_by_number_of_cpu_cores(soft_assert, node_hardwares_db_data):

    report = get_report('Number of Nodes per CPU Cores')
    for row in report.data.rows:

        hw = node_hardwares_db_data[row['Name']]

        soft_assert(hw.cpu_total_cores == int(row['Hardware Number of CPU Cores']),
                    'Hardware Number of CPU Cores is wrong for node "{}": expected {} got {}.'
                    .format(row['Name'], hw.cpu_total_cores, row['Hardware Number of CPU Cores']))


@pytest.mark.polarion('CMP-10008')
def test_report_projects_by_number_of_pods(appliance, soft_assert):

    container_projects = appliance.db['container_projects']
    container_pods = appliance.db['container_groups']

    report = get_report('Projects by Number of Pods')
    for row in report.data.rows:
        pods_count = len(container_pods.__table__.select().where(
            container_pods.container_project_id ==
            container_projects.__table__.select().where(
                container_projects.name == row['Project Name']).execute().fetchone().id
        ).execute().fetchall())

        soft_assert(pods_count == int(row['Number of Pods']),
                    'Number of pods is wrong for project "{}". expected {} got {}.'
                    .format(row['Project Name'], pods_count, row['Number of Pods']))


@pytest.mark.polarion('CMP-10009')
def test_report_projects_by_cpu_usage(soft_assert, vporizer):

    report = get_report('Projects By CPU Usage')
    for row in report.data.rows:

        vpor_values = get_vpor_data_by_name(vporizer, row["Name"])[0]
        usage_db = round(vpor_values.max_cpu_usage_rate_average, 2)
        usage_report = round(float(row['CPU Usage (%)']), 2)

        soft_assert(usage_db == usage_report,
                    'CPU usage is wrong for project "{}": expected {} got {}'
                    .format(row['Name'], usage_db, usage_report))


@pytest.mark.polarion('CMP-10010')
def test_report_projects_by_memory_usage(soft_assert, vporizer):

    report = get_report('Projects By Memory Usage')
    for row in report.data.rows:

        vpor_values = get_vpor_data_by_name(vporizer, row["Name"])[0]
        usage_db = round(vpor_values.max_mem_usage_absolute_average, 2)
        usage_report = round(float(row['Memory Usage (%)']), 2)

        soft_assert(usage_db == usage_report,
                    'CPU usage is wrong for project "{}": expected {} got {}.'
                    .format(row['Name'], usage_db, usage_report))
