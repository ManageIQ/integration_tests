# -*- coding: utf-8 -*-

import fauxfactory
from random import random
import re

import pytest

from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.containers.provider import ContainersProvider
from cfme.intelligence.chargeback import assignments, rates
from cfme.intelligence.reports.reports import CustomReport
from cfme.web_ui import flash


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.meta(
        server_roles='+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor'),
    pytest.mark.usefixtures("setup_provider_modscope")
]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')


RATE_TO_COST_HEADER = {
    'Fixed Compute Cost 1': 'Fixed Compute Cost 1',
    'Fixed Compute Cost 2': 'Fixed Compute Cost 2',
    'Used CPU Cores': 'Cpu Cores Used Cost',
    'Used Memory': 'Memory Used Cost',
    'Used Network I/O': 'Network I/O Used Cost',
}


def price2float(str_):
    """Converting the price (str) value to float (2 decimals).
    e.g. '$1,273.48' --> 1273.48"""
    if not str_:
        return 0.0
    return float(re.search('[\d\.]+', str_).group())


def new_chargeback_rate(appliance, include_variable_rates=True):

    # Create a new Chargeback compute rate

    def rand_float_str():
        return str(round(random() * fauxfactory.gen_integer(1, 20), 2))

    def gen_var_rate():
        return (rand_float_str() if include_variable_rates else 0)

    description = 'custom_rate_' + fauxfactory.gen_alphanumeric()
    data = {
        'Used CPU Cores': {'per_time': 'Hourly',
                           'fixed_rate': fauxfactory.gen_integer(1, 4),
                           'variable_rate': gen_var_rate()},
        'Fixed Compute Cost 1': {'per_time': 'Hourly',
                                 'fixed_rate': rand_float_str()},
        'Fixed Compute Cost 2': {'per_time': 'Hourly',
                                 'fixed_rate': rand_float_str()},
        'Used Memory': {'per_time': 'Hourly',
                        'fixed_rate': rand_float_str(),
                        'variable_rate': gen_var_rate()},
        'Used Network I/O': {'per_time': 'Hourly',
                             'fixed_rate': rand_float_str(),
                             'variable_rate': gen_var_rate()}
    }
    ccb = rates.ComputeRate(description, fields=data, appliance=appliance)
    ccb.create()
    return ccb


@pytest.yield_fixture(scope="module")
def new_chargeback_fixed_rate(appliance):
    # Create a new Chargeback compute fixed rate
    ccb = new_chargeback_rate(appliance, include_variable_rates=False)
    yield ccb
    ccb.delete()


@pytest.yield_fixture(scope="module")
def assign_compute_custom_rate(new_chargeback_fixed_rate, provider):
    # Assign custom Compute rate to the Selected Containers Provider
    asignment = assignments.Assign(
        assign_to="Selected Containers Providers",
        selections={
            provider.name: {'Rate': new_chargeback_fixed_rate.description}
        })
    asignment.computeassign()
    logger.info('ASSIGNING CUSTOM COMPUTE RATE')

    yield new_chargeback_fixed_rate.description

    asignment = assignments.Assign(
        assign_to="Selected Containers Providers",
        selections={
            provider.name: {'Rate': 'Default'}
        })
    asignment.computeassign()


@pytest.yield_fixture(scope="module")
def chargeback_report_custom(assign_compute_custom_rate, provider):
    # Create a Chargeback report based on a custom Compute rate; Queue the report
    title = 'report_' + assign_compute_custom_rate
    data = {'menu_name': title,
            'title': title,
            'base_report_on': 'Chargeback for Projects',
            'report_fields': ['Archived', 'Chargeback Rates', 'Fixed Compute Metric',
                              'Cpu Cores Used Cost', 'Cpu Cores Used Metric',
                              'Network I/O Used', 'Network I/O Used Cost',
                              'Fixed Compute Cost 1', 'Fixed Compute Cost 2',
                              'Memory Used', 'Memory Used Cost',
                              'Provider Name', 'Fixed Total Cost', 'Total Cost'],
            'filter_show_costs': 'Project',
            'provider': provider.name,
            'project': 'All Container Projects'}
    report = CustomReport(is_candu=True, **data)
    report.create()

    logger.info('QUEUING CUSTOM CHARGEBACK REPORT FOR {} PROVIDER'.format(provider.name))
    report.queue(wait_for_finish=True)

    yield list(report.get_saved_reports()[0].data)
    report.delete()


def abstract_test_chargeback_fixed_rate_cost(chargeback_report_custom,
                                             new_chargeback_fixed_rate,
                                             soft_assert,
                                             rate_name):

    """This is an abstract test function for test fixed rate costs.
    It's comparing the expected value that calculated by the rate
    to the value in the chargeback report
    Args:
        * chargeback_report_custom: chargeback_report_custom fixture
        * new_chargeback_fixed_rate: new_chargeback_fixed_rate fixture
        * soft_assert: soft_assert fixture
        * rate_name: The rate name as it appear in the RATE_TO_COST_HEADER keys"""

    report_header_name = RATE_TO_COST_HEADER[rate_name]

    for proj in chargeback_report_custom:
        for row in proj.rows:

            expected_value = round(float(
                new_chargeback_fixed_rate.fields[rate_name]['fixed_rate']) * 24, 2)
            found_value = price2float(row[report_header_name])

            soft_assert(found_value == expected_value,
                        'Expected charge in project "{}" for rate "{}" '
                        'is {}. got {} instead'
                        .format(row['Project Name'], report_header_name,
                                found_value, expected_value))


@pytest.mark.polarion('CMP-10164')
def test_project_chargeback_new_fixed_rate(new_chargeback_fixed_rate):
    flash.assert_success_message('Chargeback Rate "{}" was added'
                                 .format(new_chargeback_fixed_rate.description))


@pytest.mark.polarion('CMP-10165')
def test_project_chargeback_assign_compute_custom_rate(assign_compute_custom_rate):
    flash.assert_success_message('Rate Assignments saved')


@pytest.mark.long_running_env
@pytest.mark.long_running_provider
@pytest.mark.polarion('CMP-10166')
def test_project_chargeback_report_fixed_rate(chargeback_report_custom):
    assert chargeback_report_custom, 'Error in produced report, No records found'


@pytest.mark.long_running_env
@pytest.mark.long_running_provider
@pytest.mark.polarion('CMP-10185')
def test_project_chargeback_fixed_rate_1_fixed_rate(chargeback_report_custom,
                                                    new_chargeback_fixed_rate, soft_assert):
    abstract_test_chargeback_fixed_rate_cost(chargeback_report_custom,
                                             new_chargeback_fixed_rate, soft_assert,
                                             'Fixed Compute Cost 1')


@pytest.mark.long_running_env
@pytest.mark.long_running_provider
@pytest.mark.polarion('CMP-10186')
def test_project_chargeback_fixed_rate_2_fixed_rate(chargeback_report_custom,
                                                    new_chargeback_fixed_rate, soft_assert):
    abstract_test_chargeback_fixed_rate_cost(chargeback_report_custom,
                                             new_chargeback_fixed_rate, soft_assert,
                                             'Fixed Compute Cost 2')


@pytest.mark.long_running_env
@pytest.mark.long_running_provider
@pytest.mark.polarion('CMP-10187')
def test_project_chargeback_cpu_cores_fixed_rate(chargeback_report_custom,
                                                 new_chargeback_fixed_rate, soft_assert):
    abstract_test_chargeback_fixed_rate_cost(chargeback_report_custom,
                                             new_chargeback_fixed_rate, soft_assert,
                                             'Used CPU Cores')


@pytest.mark.long_running_env
@pytest.mark.long_running_provider
@pytest.mark.polarion('CMP-10189')
def test_project_chargeback_memory_used_fixed_rate(chargeback_report_custom,
                                                   new_chargeback_fixed_rate, soft_assert):
    abstract_test_chargeback_fixed_rate_cost(chargeback_report_custom,
                                             new_chargeback_fixed_rate, soft_assert,
                                             'Used Memory')


@pytest.mark.long_running_env
@pytest.mark.long_running_provider
@pytest.mark.polarion('CMP-10190')
def test_project_chargeback_network_io_fixed_rate(chargeback_report_custom,
                                                  new_chargeback_fixed_rate, soft_assert):
    abstract_test_chargeback_fixed_rate_cost(chargeback_report_custom,
                                             new_chargeback_fixed_rate, soft_assert,
                                             'Used Network I/O')
