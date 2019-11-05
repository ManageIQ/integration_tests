# -*- coding: utf-8 -*-
"""Plugin that does basic test case validation.

Use ``--validate-test-cases`` to enable it.

Currently does not work on ``--collect-only`` due to pytest's implementation bug.

Error output lines are prefixed by ``[TCV-E]``.
If no error nappens, a line prefixed with ``[TCV-OK]`` appears at the end of collection.
"""


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption(
        '--validate-test-cases', dest='validate_tcs', action='store_true', default=False,
        help="Enable test case validation")


def load_available_requirements():
    """Slightly hacky, run through all objects in the module and only pick the correct ones."""
    from _pytest.mark import MarkDecorator
    from cfme import test_requirements
    names = set()
    for requirement_name in dir(test_requirements):
        if requirement_name.startswith('_') or requirement_name == 'pytest':
            continue
        requirement_marker = getattr(test_requirements, requirement_name)
        if not isinstance(requirement_marker, MarkDecorator):
            continue
        if requirement_marker.name == 'requirement':
            names.add(requirement_marker.args[0])
    return names


def check_tier(item):
    strings = []
    tier = item.get_closest_marker('tier')
    if tier is None:
        strings.append('[TCV-E] MISSING TIER: {}'.format(item.nodeid))
    else:
        try:
            tier = tier.args[0]
        except IndexError:
            strings.append('[TCV-E] BAD TIER SPECIFICATION: {}'.format(item.nodeid))
        else:
            if not 1 <= tier <= 3:
                strings.append('[TCV-E] BAD TIER NUMBER ({}): {}'.format(tier, item.nodeid))
    return strings


def check_requirement(item, available_requirements):
    strings = []
    requirement = item.get_closest_marker('requirement')
    if requirement is None:
        strings.append('[TCV-E] MISSING REQUIREMENT: {}'.format(item.nodeid))
    else:
        try:
            requirement = requirement.args[0]
        except IndexError:
            strings.append('[TCV-E] BAD REQUIREMENT SPECIFICATION: {}'.format(item.nodeid))
        else:
            if requirement not in available_requirements:
                strings.append(
                    '[TCV-E] BAD REQUIREMENT STRING ({}): {}'.format(requirement, item.nodeid))
    return strings


def pytest_report_collectionfinish(config, startdir, items):
    if not config.option.validate_tcs:
        return
    strings = []
    available_requirements = load_available_requirements()
    for item in items:
        strings.extend(check_tier(item))
        strings.extend(check_requirement(item, available_requirements))
    if not strings:
        strings.append('[TCV-OK] TEST CASES VALIDATED OK!')
    else:
        strings.append('[TCV-E] SOME TEST CASES NEED REVIEWING!')
    return strings
