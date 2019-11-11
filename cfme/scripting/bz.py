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
from bugzilla_data import BugzillaData

from cfme.utils import conf
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.path import data_path
from cfme.utils.version import current_version

STATUS = {
    "open_bzs": {"val": "true", "text": "are open", "coverage_text": " open"},
    "closed_bzs": {"val": "false", "text": "are closed", "coverage_text": " closed"},
    "all_bzs": {"val": None, "text": "have coverage", "coverage_text": ""}
}

QUERY_PATH = data_path.join("/bugzilla-queries/")
BZ_URL = conf.env.bugzilla.url


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


def get_qe_test_coverage(info, bz_status):
    """
    Given info (what is returned from yaml.load on bz-report.yaml),
    This function screens and returns only BZs which are OPEN, if open_only=True, otherwise it
    returns all BZs
    """
    BZTestCoverage = namedtuple("BZTestCoverage", ["id", "qe_test_coverage"])

    bz_list = []
    for bug_id in info.keys():
        if bz_status == "open_bzs" and info[bug_id]["is_open"] == "false":
            continue
        if bz_status == "closed_bzs" and info[bug_id]["is_open"] == "true":
            continue

        # get qe_test_coverage_flag
        qe_test_coverage = "?"
        for flag in info[bug_id]["flags"]:
            if flag["name"] == "qe_test_coverage":
                qe_test_coverage = flag["status"]
                break

        # append the BZ if its coverage isn't correct
        if qe_test_coverage != "+":
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


@main.command(help="Generate BZ report on bugs going into a z-stream")
@click.option(
    "--version",
    "-v",
    "version",
    default=lambda: current_version().vstring,
    help="Version for which to get BZs (e.g. 5.10.11.0)",
    show_default=True
)
@click.option(
    "--query-file",
    "-q",
    "query_file",
    default="fixed_in_query.yaml",
    help="Template query file",
    show_default=True
)
@click.option(
    "--output",
    "-o",
    "output",
    is_flag=True,
    default=False,
    show_default=True,
    help="Show information about BZs in the terminal"
)
@click.option(
    "--filename",
    "-f",
    "fname",
    default=lambda: f"bz-report-{current_version().vstring}.yaml",
    help="Filename into which the report is written (must be yaml file)"
)
def build_report(version, query_file, output, fname):
    query_path = QUERY_PATH.join(query_file)
    bz_data = BugzillaData(
        query_path,
        BZ_URL,
        "component",
        login=True,
        credentials=conf.credentials.bugzilla
    )
    # overide query with current stream
    bz_data.query["fixed_in"] = [version]
    if output:
        click.echo(bz_data.generate_output())

    click.echo(f"Generating a bz report at {fname}")
    bz_data.generate_report(filename=fname)


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
        bz_list = [bug_id for bug_id
                   in list(info.keys())
                   if info[bug_id]["is_open"] == status["val"]]
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
@click.option(
    "--all",
    "-a",
    "bz_status",
    is_flag=True,
    help="Audit test coverage on all BZs",
    default=True,
    show_default=True,
    flag_value="all_bzs",
)
@click.option(
    "--open",
    "-o",
    "bz_status",
    is_flag=True,
    help="Audit test coverage on only open BZs",
    default=False,
    show_default=True,
    flag_value="open_bzs"
)
@click.option(
    "--closed",
    "-c",
    "bz_status",
    is_flag=True,
    help="Audit test coverage on only closed BZs",
    default=False,
    show_default=True,
    flag_value="closed_bzs"
)
def coverage(directory, set_bzs, bz_status):
    info = get_report(directory)

    # get list of bzs that should have test coverage set
    bz_list = get_qe_test_coverage(info, bz_status)

    click.echo("\nThe following{} BZs should have qe_test_coverage set to '+': ".format(
        STATUS[bz_status]["coverage_text"])
    )
    for bz in bz_list:
        click.echo("    id: {}, qe_test_coverage: {}".format(bz.id, bz.qe_test_coverage))

    if set_bzs:
        click.echo("Setting qe_test_coverage on the above BZs to '+'...")
        ids = [int(bz.id)for bz in bz_list]
        BZ.bugzilla.set_flags(ids, {"qe_test_coverage": "+"})
        click.echo("Done.")

    # remove bz-report.yaml
    cleanup()
