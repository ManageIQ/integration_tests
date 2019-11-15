"""Collection of fixtures for simplified work with bzs.

The main purpose of this file is to add a pytest option which generates a BZ report. This option
gives information about the BZs that appear as coverage/automates metadata in test functions.
"""
import yaml

from cfme.fixtures.pytest_store import store
from cfme.utils.blockers import BZ


def pytest_addoption(parser):
    group = parser.getgroup('Blocker options')
    group.addoption(
        '--generate-bz-report',
        action='store_true',
        default=False,
        dest='generate_bz_report',
        help='Generate a BZ report based on the automates/coverage metadata of test cases.'
    )


def pytest_collection_modifyitems(session, config, items):
    if not config.getvalue("generate_bz_report"):
        return
    store.terminalreporter.write("Loading automated/covered BZs ...\n", bold=True)
    bz_list = []
    for item in items:
        if "automates" not in item._metadata and "coverage" not in item._metadata:
            continue
        # get list of bzs with coverage
        if "automates" in item._metadata:
            bz_list.extend(item._metadata["automates"])
        if "coverage" in item._metadata:
            bz_list.extend(item._metadata["coverage"])

    if bz_list:
        # remove duplicate BZs
        bz_list = list(dict.fromkeys(bz_list))
        # remove references that are an instance of BZ
        bz_list = [bug.bug_id if isinstance(bug, BZ) else bug for bug in bz_list]
        # get BZ info
        info = BZ.bugzilla.get_bz_info(bz_list)
        # output BZ info to yaml
        with open("bz-report.yaml", "w") as outfile:
            yaml.dump(info, outfile, default_flow_style=False)
    else:
        store.terminalreporter.write(
            "ERROR: No BZs marked with 'automates'/'coverage' in that test module. A report will "
            "not be generated.\n", bold=True
        )
