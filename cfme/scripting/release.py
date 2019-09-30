#!/usr/bin/env python3
import re
import sys
from collections import defaultdict

import click
import github
import tabulate

from cfme.utils.conf import docker


REPO_NAME = "ManageIQ/integration_tests"

HEADERS = ['PR', 'Labels', 'Author', 'Title']
FULL_HEADERS = HEADERS + ['DESCRIPTION']

VALID_LABELS = [
    "ansible",
    "blackify",
    "blockers-only",
    "collections-conversion",
    "customer-case",
    "doc",
    "enhancement",
    "fix-framework",
    "fix-locator-or-text",
    "fix-test",
    "implement-ssui",
    "infra-related",
    "issue-bug",
    "issue-rfe",
    "LegacyBranch",
    "manual",
    "new-test-or-feature",
    "Nuage",
    "other",
    "py3-compat",
    "rc-regression-fix",
    "Redfish",
    "requirements",
    "RHV",
    "sprout",
    "tech-debt",
    "test-automation",
    "test-cleanup",
    "widgetastic-conversion",
]

IGNORED_LABELS = ['lint-ok', 'WIP-testing']

PR_LINK = "[{pr}](https://github.com/ManageIQ/integration_tests/pull/{pr})"


def clean_commit(commit_msg):
    replacements = ["1LP", "RFR", "WIP", "WIPTEST", "NOTEST"]
    for replacement in replacements:
        commit_msg = commit_msg.replace("[{}]".format(replacement), "")
    return commit_msg.strip(" ")


def clean_body(string):
    if string is None:
        string = ""
    pytest_match = re.findall(r"({{.*}}\s*)", string, flags=re.S | re.M)
    if pytest_match:
        string = string.replace(pytest_match[0], "")
    return string


def get_prs(release, old_release, gh):
    """Get merged PRs between the given releases"""

    # GH searching supports by date, so get dates for the release objects
    old_date = old_release.created_at.date().isoformat()  # iso 8601 date
    new_date = release.created_at.date().isoformat()

    pulls = gh.search_issues(
        "",  # empty query string, required positional arg
        type="pr",
        repo=REPO_NAME,
        merged=f'{old_date}..{new_date}',  # gh query format for range
    )

    prs = []
    pr_nums_without_label = []
    for pr in pulls:
        prs.append(pr)
        for label in pr.labels:
            if label.name in VALID_LABELS:
                pr.label = label.name
                break
        else:
            pr_nums_without_label.append(pr.number)

    if pr_nums_without_label:
        print(
            "ERROR: The following PRs don't have any of recognized labels: \n",
            "\n".join(pr_nums_without_label),
        )
        print("Recognized labels:", ", ".join(VALID_LABELS))
        sys.exit(1)
    return prs


@click.command(help="Assist in generating release changelog")
@click.argument("tag")
@click.option(
    "--old-tag",
    help="Build the changelog from a previous tag",
)
@click.option(
    "--full",
    "report_type",
    flag_value="full",
    help="Generates a full report with all PR description",
)
@click.option(
    "--brief",
    "report_type",
    flag_value="brief",
    default=True,
    help="Generates report with PR, label, author, and title in 4 columns"
)
@click.option(
    "--stats",
    "report_type",
    flag_value="stats",
    help="Generates stats only report"
)
@click.option(
    "--all",
    "report_type",
    flag_value="all",
    help="Generates stats and brief report together"
)
@click.option(
    "--links/--no-links",
    default=False,
    help="Include PR links in markdown"
)
@click.option(
    "--format",
    "tableformat",
    default='github',
    type=click.Choice(tabulate.tabulate_formats, case_sensitive=True),
    help="The tablefmt option for python tabulate"
)
def main(tag, old_tag, report_type, links, tableformat):
    """Script to assist in generating the release changelog

    This script will generate a simple or full diff of PRs that are merged
    and present the data in a way that is easy to copy/paste into an email
    or git tag.
    """

    print(f"Report Includes: {old_tag} -> {tag}")

    gh = github.Github(docker.gh_token)
    repo = gh.get_repo(REPO_NAME)
    release = repo.get_release(tag)
    old_release = repo.get_release(old_tag)

    prs = get_prs(release, old_release, gh)

    if report_type in ("full", "brief", "all"):
        # Print a markdown table of PR attributes, including description for full report type
        report_data = []
        for pr in prs:
            pr_attrs = [
                pr.number if not links else PR_LINK.format(pr=pr.number),
                ', '.join(label.name for label in pr.labels if label.name in VALID_LABELS),
                pr.user.login,
                clean_commit(pr.title)
            ]
            if report_type == 'full':
                pr_attrs.append(clean_body(pr.body))
            report_data.append(pr_attrs)

        print(tabulate.tabulate(report_data,
                                headers=FULL_HEADERS if report_type == 'full' else HEADERS,
                                tablefmt=tableformat))

    elif report_type in ["stats", "all"]:
        labels = defaultdict(int)
        authors = defaultdict(int)

        for pr in prs:
            for label_name in [l.name for l in pr.labels if l.name not in IGNORED_LABELS]:
                labels[label_name] += 1
            authors[pr.user.login] += 1

        # Label stats
        print(tabulate.tabulate(sorted(labels.items(),
                                       key=lambda item: item[1],
                                       reverse=True),
                                headers=["Label", "Number of PRs"],
                                tablefmt=tableformat))

        print('======================================')

        # Author stats
        print(tabulate.tabulate(sorted(authors.items(),
                                       key=lambda item: item[1],
                                       reverse=True),
                                headers=["Author", "Number of PRs"],
                                tablefmt=tableformat))


if __name__ == "__main__":
    main()
