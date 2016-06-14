"""skipper: Autmatically skip tests with certain marks as defined in this module

This doesn't provide any special markers, but it does add behavor to marks defined in
:py:attr:`skip_marks`.

"""
import pytest

from fixtures.pytest_store import store

#: List of (mark, commandline flag) tuples. When the given mark is used on a test, it will
#: be skipped unless the commandline flag is used. If the mark is already found in py.test's
#: parsed mark expression, no changes will be made for that mark.
skip_marks = [
    ('long_running', '--long-running'),
    ('perf', '--perf')
]

_mark_doc = ('{mark}: Skip tests with the {mark} mark by default, unless {cmdline} commandline '
    'is used or the corresponding mark expression is used (e.g. "py.test -m {mark}")')


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    for dest, cmdline_opt in skip_marks:
        group.addoption(cmdline_opt, dest=dest, action='store_true', default=False,
            help="Run tests with the 'pytest.mark.{}' mark, which are skipped by default"
            .format(dest))


def pytest_configure(config):
    marks_to_skip = []
    mark_expr = [mark.strip(''''"()''') for mark in config.option.markexpr.split()]
    for dest, cmdline_opt in skip_marks:
        ignore_mark = getattr(config.option, dest)
        config.addinivalue_line('markers', _mark_doc.format(mark=dest, cmdline=cmdline_opt))
        # Comparing against the mark_expr split/strip attempts to match just the mark words exactly;
        # if we make a mark called 'not' or 'in', I think we're asking for trouble anyway,
        # so this is probably a sane and simple way to prevent false positive matches
        if dest in mark_expr and ignore_mark:
            # If the mark is in the mark expression already and the commandline flag exists,
            # report the conflict to the terminal
            store.terminalreporter.write_line('{} already in cmdline mark expression, '
                '{} flag ignored'.format(dest, cmdline_opt), yellow=True)
            continue
        elif dest in mark_expr or ignore_mark:
            # No need to log anything if there's no mark_expr / commandline flag conflict
            continue
        else:
            marks_to_skip.append(dest)

    # Build all the marks to skip into one flat mark expression rather than nesting
    skip_mark_expr = ' and '.join(['not {}'.format(mark) for mark in marks_to_skip])

    # modify (or set) the mark expression to exclude tests as configured by the commandline flags
    if skip_mark_expr:
        if config.option.markexpr:
            config.option.markexpr = '({}) and ({})'.format(skip_mark_expr, config.option.markexpr)
        else:
            config.option.markexpr = skip_mark_expr


def pytest_collection_modifyitems(items):
    # mark all perf tests here so we don't have to maintain the mark in those modules
    for item in items:
        if item.nodeid.startswith('cfme/tests/perf'):
            item.add_marker(pytest.mark.perf)
