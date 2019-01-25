import py
import pytest
import cfme
import subprocess
import sys

ROOT = py.path.local(cfme.__file__).dirpath()

MODULES = sorted(x for x in ROOT.visit("*.py") if 'test_' not in x.basename)

KNOWN_FAILURES = set(ROOT.dirpath().join(x) for x in[
    'cfme/utils/ports.py',  # module object
    'cfme/utils/dockerbot/check_prs.py',  # unprotected script
    'cfme/utils/conf.py',  # config object that replaces the module
    'cfme/intelligence/rss.py',  # import loops
    'cfme/intelligence/timelines.py',
    'cfme/intelligence/chargeback/rates.py',
    'cfme/intelligence/chargeback/assignments.py',
    'cfme/intelligence/chargeback/__init__.py',
    'cfme/fixtures/widgets.py',
    'cfme/dashboard.py',
    'cfme/configure/tasks.py',
])


@pytest.mark.parametrize('module_path', MODULES, ids=ROOT.dirpath().bestrelpath)
@pytest.mark.long_running
def test_import_own_module(module_path):
    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    if module_path in KNOWN_FAILURES:
        pytest.skip("{} is a known failed path".format(ROOT.dirpath().bestrelpath(module_path)))
    subprocess.check_call(
        [sys.executable, '-c',
        'import sys, py;py.path.local(sys.argv[1]).pyimport()', str(module_path)])
