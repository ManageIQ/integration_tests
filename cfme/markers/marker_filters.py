"""Marker definitions for tier and requirement, and meta filter plugin

"""
import re

from cfme.fixtures.pytest_store import store


TEST_PARAM_FILTER = re.compile(r"\[.*\]")


# Markers
def pytest_configure(config):
    if config.getoption('--help'):
        return
    markers_to_add = [
        'tier: mark a test case with a tier',
        'requirement: mark a test case with a requirement',
        'customer_scenario: mark a test case as a customer story',
        'rfe: mark a test case as an RFE'
    ]
    for marker in markers_to_add:
        config.addinivalue_line('markers', marker)


# Filtering options
def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--tier',
                    type=int,
                    action='append',
                    help='only run tests of the given tier levels')
    group.addoption('--requirement',
                    type=str,
                    action='append',
                    help='only run tests with given requirement markers')
    group.addoption('--customer-scenario',
                    action='store_true',
                    default=False,
                    help='only run tests marked with customer_scenario')


def pytest_collection_modifyitems(session, config, items):
    """Provide filtering of test case collection based on the CLI options"""
    tiers = config.getoption('tier')
    requirements = config.getoption('requirement')
    customer = config.getoption('customer_scenario')
    if not tiers and not requirements and not customer:
        return
    # TODO(rpfannsc) trim after pytest #1373 is done
    keep, discard_tier, discard_requirement, discard_customer = [], [], [], []

    for item in items:
        # for each filter, check if its active and that the item has the marker
        # Then check if the marker content matches the passed filter
        # Discard items without the matching value
        if tiers and getattr(item.get_closest_marker('tier'), 'args', [False])[0] not in tiers:
            discard_tier.append(item)
            continue
        if requirements and getattr(item.get_closest_marker('requirement'), 'args',
                [False])[0] not in requirements:
            discard_requirement.append(item)
            continue
        if customer and not item.get_closest_marker('customer_scenario'):
            discard_customer.append(item)
            continue
        keep.append(item)

    items[:] = keep
    # TODO(rpfannsc) add a reason after pytest #1372 is fixed
    discarded = discard_tier + discard_requirement + discard_customer
    config.hook.pytest_deselected(items=discarded)
    if tiers:
        store.uncollection_stats['tier mark'] = len(discard_tier)
    if requirements:
        store.uncollection_stats['requirement mark'] = len(discard_requirement)
    if customer:
        store.uncollection_stats['customer_scenario mark'] = len(discard_customer)
