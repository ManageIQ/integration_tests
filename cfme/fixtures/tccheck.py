# -*- coding: utf-8 -*-
"""Plugin that does basic test case validation.

Use ``--validate-test-cases`` to enable it.

Currently does not work on ``--collect-only`` due to pytest's implementation bug.

All output lines are prefixed by ``[TCVE]``.
"""


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption(
        '--validate-test-cases', dest='validate_tcs', action='store_true', default=False,
        help="Enable test case validation")


def pytest_report_collectionfinish(config, startdir, items):
    if not config.option.validate_tcs:
        return
    strings = []
    for item in items:
        tier = item.get_marker('tier')
        if tier is None:
            strings.append('[TCVE] MISSING TIER: {}'.format(item.nodeid))
        else:
            try:
                tier = tier.args[0]
            except IndexError:
                strings.append('[TCVE] BAD TIER SPECIFICATION: {}'.format(item.nodeid))
            else:
                if not 1 <= tier <= 3:
                    strings.append('[TCVE] BAD TIER NUMBER: {}'.format(item.nodeid))

        requirement = item.get_marker('requirement')
        if requirement is None:
            strings.append('[TCVE] MISSING REQUIREMENT: {}'.format(item.nodeid))
        else:
            try:
                requirement = requirement.args[0]
            except IndexError:
                strings.append('[TCVE] BAD REQUIREMENT SPECIFICATION: {}'.format(item.nodeid))
    return strings
