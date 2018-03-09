# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import re

import cfme.intelligence.chargeback.assignments as cb
import cfme.intelligence.chargeback.rates as rates
from cfme import test_requirements
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.chargeback
]


@pytest.yield_fixture(scope="module")
def assign_custom_rate(new_compute_rate, provider):
    # Assign custom Compute rate to the Enterprise and then queue the Chargeback report.
    description = new_compute_rate
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': description}
        })
    enterprise.computeassign()
    enterprise.storageassign()
    logger.info('Assigning CUSTOM Compute rate')

    yield

    # Resetting the Chargeback rate assignment
    enterprise = cb.Assign(
        assign_to="The Enterprise",
        selections={
            'Enterprise': {'Rate': '<Nothing>'}
        })
    enterprise.computeassign()
    enterprise.storageassign()


@pytest.yield_fixture(scope="module")
def new_compute_rate():
    # Create a new Compute Chargeback rate
    try:
        desc = 'custom_' + fauxfactory.gen_alphanumeric()
        compute = rates.ComputeRate(description=desc,
                    fields={'Used CPU':
                            {'per_time': 'Daily', 'variable_rate': '3'},
                            'Used Disk I/O':
                            {'per_time': 'Daily', 'variable_rate': '2'},
                            'Used Memory':
                            {'per_time': 'Daily', 'variable_rate': '2'}})
        compute.create()
        storage = rates.StorageRate(description=desc,
                fields={'Used Disk Storage':
                    {'per_time': 'Daily', 'variable_rate': '3'}})
        storage.create()
        yield desc
    finally:
        compute.delete()
        storage.delete()


def test_validate_cpu_usage_cost_daily_cost(chargeback_costs_default, chargeback_report_default):
    """Test to validate CPU usage cost.
       Calculation is based on default Chargeback rate.
    """
    for groups in chargeback_report_default:
        if groups["CPU Used Cost"]:
            estimated_cpu_usage_cost = chargeback_costs_default['cpu_used_cost']
            cost_from_report = groups["CPU Used Cost"]
            cost = re.sub(r'[$,]', r'', cost_from_report)
            assert estimated_cpu_usage_cost - 1.0 <= float(cost) \
                <= estimated_cpu_usage_cost + 1.0, 'Estimated cost and report cost do not match'
            break
