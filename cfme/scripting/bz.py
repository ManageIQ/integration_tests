"""
Scripts for dealing with Bugzilla metadata, listing BZs with coverage, and setting qe_test_coverage
flag. This script looks at test-case metadata for the flags "automates" and "coverage", and fetches
information about the BZs listed there.

For usage see, "miq bz --help"

The basic usage of this command is via
    .. code-block:: python
    >>> miq bz <command> <directory>
where <command> is one of report, list, or coverage, and <directory> is the testing directory, e.g.
"cfme/tests/control/"

To list BZs that this script would set coverage for, you can do,
    .. code-block:: python
    >>> miq bz coverage <directory>
This will print out the ids of BZs that could have qe_test_coverage switched to '+'
To then set qe_test_coverage on those BZs, you can do,
    .. code-block:: python
    >>> miq bz coverage --set <directory>
"""
import os
import sys
from collections import namedtuple

import click
import pytest
import yaml

from cfme.utils.blockers import BZ
from cfme.utils.log import logger

STATUS = {
    "open_bzs": {"val": "true", "text": "are open"},
    "closed_bzs": {"val": "false", "text": "are closed"},
    "all_bzs": {"val": None, "text": "have coverage"}
}


def get_report(directory):
    click.echo("Generating a BZ report in bz-report.yaml")
    pytest.main([
        "--use-provider", "complete",
        "--long-running",
        "--use-template-cache",
        "--collect-only",
        "-q",
        "--generate-bz-report", directory
    ])
    # read the generated yaml
    try:
        with open("bz-report.yaml", "r") as stream:
            info = yaml.load(stream, Loader=yaml.BaseLoader)
    except IOError:
        msg = (
            "ERROR: File bz-report.yaml not found, something went wrong during report generation.\n"
            "       Likely no BZs were found in {} with 'automates'/'coverage',"
            " so a report wasn't generated.".format(directory)
        )
        click.secho(msg, err=True, bold=True, fg="red")
        sys.exit(0)
    return info


def get_qe_test_coverage(info, open_only=True):
    """
    Given info (what is returned from yaml.load on bz-report.yaml),
    This function screens and returns only BZs which are OPEN, if open_only=True, otherwise it
    returns all BZs
    """
    BZTestCoverage = namedtuple("BZTestCoverage", ["id", "qe_test_coverage"])

    bz_list = []
    for bug_id in info.keys():
        if open_only and info[bug_id]["is_open"] == "false":
            continue
        # get qe_test_coverage_flag
        qe_test_coverage = "?"
        for flag in info[bug_id]["flags"]:
            if flag["name"] == "qe_test_coverage":
                qe_test_coverage = flag["status"]
                break
        # append the BZ
        bz_list.append(BZTestCoverage(id=bug_id, qe_test_coverage=qe_test_coverage))

    return bz_list


def cleanup():
    click.echo("Removing the BZ report file, bz-report.yaml")
    try:
        os.remove("bz-report.yaml")
    except OSError:
        logger.exception("bz-report.yaml not found")


@click.group(help="Functions for generating reports on BZs included in test suite metadata")
def main():
    pass


@main.command(help="Generate BZ report on BZs that have coverage given a directory")
@click.argument("directory", default="cfme/tests/")
def report(directory):
    get_report(directory)


@main.command(help="List open/closed BZs that have test coverage")
@click.argument("directory", default="cfme/tests/")
@click.option(
    "--all",
    "-a",
    "bz_status",
    is_flag=True,
    help="list all BZs with coverage",
    default=True,
    show_default=True,
    flag_value="all_bzs",
)
@click.option(
    "--open",
    "-o",
    "bz_status",
    is_flag=True,
    help="list open BZs with coverage",
    default=False,
    show_default=True,
    flag_value="open_bzs"
)
@click.option(
    "--closed",
    "-c",
    "bz_status",
    is_flag=True,
    help="list closed BZs with coverage",
    default=False,
    show_default=True,
    flag_value="closed_bzs"
)
def list(directory, bz_status):
    info = get_report(directory)

    # get dict of information
    status = STATUS[bz_status]

    if status["val"]:
        bz_list = [bug_id for bug_id in info.keys() if info[bug_id]["is_open"] == status["val"]]
    else:
        bz_list = [bug_id for bug_id in info.keys()]

    if bz_list:
        click.echo("The following BZ's {}: \n{}".format(status["text"], "\n".join(bz_list)))
    else:
        click.echo("I found no BZ's that {} BZ's".format(status["text"]))
    cleanup()


@main.command(help="Set QE test coverage flag based on automates/coverage metadata")
@click.argument("directory", default="cfme/tests")
@click.option(
    "-s",
    "--set",
    "set_bzs",
    is_flag=True,
    help="Set QE test coverage on BZs that are marked in coverage/auotmates test metadata",
    default=False,
    show_default=True
)
def coverage(directory, set_bzs):
    info = get_report(directory)

    # get list of open BZs that are open and should have test coverage set
    bz_list = get_qe_test_coverage(info, open_only=True)

    click.echo("\nThe following BZs should have qe_test_coverage set to '+': ")
    for bz in bz_list:
        click.echo("    id: {}, qe_test_coverage: {}\n".format(bz.id, bz.qe_test_coverage))

    if set_bzs:
        click.echo("Setting qe_test_coverage on the above BZs to '+'...")
        ids = [int(bz.id)for bz in bz_list]
        BZ.bugzilla.set_flags(ids, {"qe_test_coverage": "+"})
        click.echo("Done.")

    # remove bz-report.yaml
    cleanup()
