#!/usr/bin/env python3
import datetime
import re
import sys
import textwrap
from collections import defaultdict

import click
import git
import github
import tabulate

from cfme.utils.conf import docker

LINE_FMT = "{pr:<{pr_len}} | {label:<{label_len}} | "


def clean_commit(commit_msg):
    replacements = ["1LP", "RFR", "WIP", "WIPTEST", "NOTEST"]
    for replacement in replacements:
        commit_msg = commit_msg.replace("[{}]".format(replacement), "")
    return commit_msg.strip(" ")


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
    "test-cleanup",
    "widgetastic-conversion",
]


def pr_numbers_in_commit_order(commits, prs):
    for commit in commits:
        pr = re.match(r".*[#](\d+).*", commit.summary)
        if pr:
            pr_number = int(pr.groups()[0].replace("#", ""))
            if pr_number in prs:
                yield pr_number


def clean_body(string):
    if string is None:
        string = ""
    pytest_match = re.findall(r"({{.*}}\s*)", string, flags=re.S | re.M)
    if pytest_match:
        string = string.replace(pytest_match[0], "")
    return string


def get_prs():

    now = datetime.date.today()
    start_of_week = now - datetime.timedelta(days=30)
    string_start = start_of_week.strftime("%Y-%m-%d")
    # todo get date from last tag commit

    gh = github.Github(docker.gh_token)

    pulls = gh.search_issues(
        "",
        type="pr",
        repo="{d.gh_owner}/{d.gh_repo}".format(d=docker),
        merged=">" + string_start,
    )

    prs = {}
    pr_nums_without_label = []
    for pr in pulls:
        prs[pr.number] = pr
        for label in pr.labels:
            if label.name in VALID_LABELS:
                pr.label = label.name
                break
        else:
            pr_nums_without_label.append(str(pr.number))

    if pr_nums_without_label:
        print(
            "ERROR: The following PRs don't have any of recognized labels:",
            ", ".join(pr_nums_without_label),
        )
        print("Recognized labels:", ", ".join(VALID_LABELS))
        sys.exit(1)
    return prs


@click.command(help="Assist in generating release changelog")
@click.argument("tag")
@click.option(
    "--old-tag",
    default=None,
    help="Build the changelog from an older tag, instead of git describe",
)
@click.option(
    "--full",
    "report_type",
    flag_value="full",
    default=True,
    help="Generates a full report with all PR description",
)
@click.option(
    "--brief", "report_type", flag_value="brief", help="Generates brief report"
)
@click.option(
    "--stats", "report_type", flag_value="stats", help="Generates stats only report"
)
@click.option("--line-limit", default="80", help="Line length limit", type=int)
def main(tag, old_tag, report_type, line_limit):
    """Script to assist in generating the release changelog

    This script will generate a simple or full diff of PRs that are merged
    and present the data in a way that is easy to copy/paste into an email
    or git tag.
    """

    repo = git.Repo(".")
    if old_tag is None:
        old_tag = repo.git.describe(tags=True, abbrev=0)

    commits = list(repo.iter_commits("{}..master".format(old_tag)))

    print("integration_tests {} Released".format(tag))
    print("")
    print("Includes: {} -> {}".format(old_tag, tag))

    max_len_labels = max(list(map(len, VALID_LABELS)))

    prs = get_prs()

    if report_type in ("full", "brief"):
        max_len_pr = len(str(max(prs)))
        followup_line = first_line = LINE_FMT.format(
            pr="", pr_len=max_len_pr, label="", label_len=max_len_labels
        )
        for pr_number in pr_numbers_in_commit_order(commits, prs):
            label = prs[pr_number].label
            title = clean_commit(prs[pr_number].title)
            first_line = LINE_FMT.format(
                pr=pr_number, pr_len=max_len_pr, label=label, label_len=max_len_labels
            )

            if report_type == "full":
                print("=" * line_limit)

            title = textwrap.wrap(title, line_limit - len(followup_line))
            print(first_line + title[0])
            for line in title[1:]:
                print(followup_line + line)

            if report_type == "full":

                print("-" * line_limit)
                string = clean_body(prs[pr_number].body)
                print(
                    "\n".join(
                        textwrap.wrap(string, line_limit, replace_whitespace=False)
                    )
                )
                print("=" * line_limit)
                print("")

    elif report_type == "stats":
        labels = defaultdict(int)
        for pr_number in pr_numbers_in_commit_order(commits, prs):
            labels[prs[pr_number].label] += 1

        print(tabulate.tabulate(sorted(labels.items()), headers=["Label", "Number"]))


if __name__ == "__main__":
    main()
