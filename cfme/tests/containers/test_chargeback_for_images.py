# -*- coding: utf-8 -*-

import fauxfactory
from random import random

import pytest

from utils import testgen
from utils.log import logger
from utils.providers import list_providers_by_class
from cfme.containers.provider import ContainersProvider
from cfme.intelligence import chargeback as cb
from cfme.intelligence.reports.reports import CustomReport


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.meta(
        server_roles='+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor'),
    pytest.mark.usefixtures('setup_provider')
]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


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
    ccb = cb.ComputeRate(description, fields=data, appliance=appliance)
    ccb.create()
    return ccb


@pytest.fixture(scope='module')
def provider_name():
    # Since 'provider' fixture is a 'function' scoped, we use this
    # fixture to yield the provider name
    return list_providers_by_class(ContainersProvider)[-1].name


@pytest.yield_fixture(scope="module")
def new_chargeback_fixed_rate(appliance):
    # Create a new Chargeback compute fixed rate
    ccb = new_chargeback_rate(appliance, include_variable_rates=False)
    yield ccb
    ccb.delete()


@pytest.yield_fixture(scope="module")
def assign_compute_custom_rate(new_chargeback_fixed_rate, provider_name):
    # Assign custom Compute rate to the Selected Containers Provider
    asignment = cb.Assign(
        assign_to="Labeled Container Images",
        docker_labels="Architecture",
        selections={
            'x86_64': new_chargeback_fixed_rate.description
        })
    asignment.computeassign()
    logger.info('ASSIGNING COMPUTE RATE FOR LABELED CONTAINER IMAGES')

    yield new_chargeback_fixed_rate.description

    asignment = cb.Assign(
        assign_to="Selected Containers Providers",
        selections={
            provider_name: "Default"
        })
    asignment.computeassign()


@pytest.yield_fixture(scope="module")
def chargeback_report_custom(assign_compute_custom_rate, provider_name):
    # Create a Chargeback report based on a custom Compute rate; Queue the report
    title = 'report_' + assign_compute_custom_rate
    data = {'menu_name': title,
            'title': title,
            'base_report_on': 'Chargeback Container Images',
            'report_fields': ['Archived', 'Chargeback Rates', 'Fixed Compute Metric',
                              'Cpu Cores Used Cost', 'Cpu Cores Used Metric',
                              'Network I/O Used', 'Network I/O Used Cost',
                              'Fixed Compute Cost 1', 'Fixed Compute Cost 2',
                              'Memory Used', 'Memory Used Cost',
                              'Provider Name', 'Fixed Total Cost', 'Total Cost'],
            'filter_show_costs': 'Container Image',
            'provider': provider_name}
    report = CustomReport(is_candu=True, **data)
    report.create()

    logger.info('QUEUING CUSTOM CHARGEBACK REPORT FOR CONTAINER IMAGE')
    report.queue(wait_for_finish=True)

    yield list(report.get_saved_reports()[0].data)
    report.delete()


@pytest.mark.polarion('CMP-10432')
def test_image_chargeback_fixed_rate(chargeback_report_custom, provider):
    assert chargeback_report_custom, 'Error in produced report, No records found'
