#!/usr/bin/env python2
from __future__ import print_function

from collections import defaultdict
import datetime
import re
import requests
import subprocess
import textwrap

import click

from cfme.utils.conf import docker


def clean_commit(commit_msg):
    replacements = ['1LP', 'RFR', 'WIP', 'WIPTEST', 'NOTEST']
    for replacement in replacements:
        commit_msg = commit_msg.replace('[{}]'.format(replacement), '')
    return commit_msg.strip(" ")


@click.command(help="Assist in generating release changelog")
@click.argument('tag')
@click.option('--old-tag', default=None,
              help='Build the changelog from an older tag, instead of git describe')
@click.option('--full', 'report_type', flag_value='full',
              default=True, help="Generates a full report with all PR description")
@click.option('--brief', 'report_type', flag_value='brief',
              help="Generates brief report")
@click.option('--stats', 'report_type', flag_value='stats',
              help="Generates stats only report")
@click.option('--line-limit', default='80', help='Line length limit')
def main(tag, old_tag, report_type, line_limit):
    """Script to assist in generating the release changelog

    This script will generate a simple or full diff of PRs that are merged
    and present the data in a way that is easy to copy/paste into an email
    or git tag.
    """
    line_length = int(line_limit)

    if not old_tag:
        proc = subprocess.Popen(['git', 'describe', '--tags', '--abbrev=0'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        old_tag = proc.stdout.read().strip("\n")
    else:
        old_tag = old_tag
    proc = subprocess.Popen(['git', 'log', '{}..master'.format(old_tag), '--oneline'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    commits = proc.stdout.read()

    valid_labels = [
        u'fix-locator-or-text', u'infra-related', u'fix-test', u'doc',
        u'other', u'enhancement', u'fix-framework', u'new-test-or-feature', u'tech-debt',
        u'widgetastic-conversion', u'collections-conversion', u'sprout'
    ]

    print('integration_tests {} Released'.format(tag))
    print('')
    print('Includes: {} -> {}'.format(old_tag, tag))

    max_len_labels = len(reduce((lambda x, y: x if len(x) > len(y) else y), valid_labels))

    now = datetime.date.today()
    start_of_week = now - datetime.timedelta(days=30)
    string_start = start_of_week.strftime('%Y-%m-%d')

    headers = {'Authorization': 'token {}'.format(docker['gh_token'])}
    items = []
    result = requests.get(
        'https://api.github.com/search/issues?per_page=200&q=type:pr+repo:{}/'
        '{}+merged:>{}'.format(docker['gh_owner'], docker['gh_repo'], string_start),
        headers=headers)
    items += result.json()['items']
    if 'Link' in result.headers:
        while re.findall('\<(.*)\>; rel="next"', result.headers['Link']):
            result = requests.get(re.findall('\<(.*)\>; rel="next"', result.headers['Link'])[0],
                                  headers=headers)
            items += result.json()['items']

    prs = {}
    pr_nums_without_label = []
    for pr in items:
        prs[pr['number']] = pr
        for label in pr['labels']:
            if label['name'] in valid_labels:
                pr['label'] = label['name']
                break
        else:
            pr_nums_without_label.append(str(pr['number']))

    if pr_nums_without_label:
        print("ERROR: The following PRs don't have any of recognized labels: {}"
              .format(', '.join(pr_nums_without_label)))
        print("Recognized labels: {}".format(', '.join(valid_labels)))
        return 1

    if report_type in ['full', 'brief']:
        max_len_pr = len(
            reduce((lambda x, y: str(x) if len(str(x)) > len(str(y)) else str(y)), prs.keys()))

        for commit in commits.split("\n"):
            pr = re.match('.*[#](\d+).*', commit)
            if pr:
                pr_number = int(pr.groups()[0].replace("#", ''))
                if pr_number in prs:
                    old_lab = prs[pr_number]['label']
                    label = old_lab + " " * (max_len_labels - len(old_lab))
                    title = clean_commit(prs[pr_number]['title'])
                    title = textwrap.wrap(title, line_length - 6 - max_len_pr - max_len_labels)
                    msg = "{} | {} | {}".format(
                        pr_number, label, title[0])
                    for line in title[1:]:
                        msg += "\n{} | {} | {}".format(
                            " " * max_len_pr, " " * max_len_labels, line.encode('ascii', 'ignore'))
                    if report_type == "full":
                        print("=" * line_length)
                    print(msg)
                    if report_type == "full":
                        print("-" * line_length)
                        string = prs[pr_number]['body']
                        if string is None:
                            string = ""
                        pytest_match = re.findall("({{.*}}\s*)", string, flags=re.S | re.M)
                        if pytest_match:
                            string = string.replace(pytest_match[0], '')
                        print("\n".join(
                            textwrap.wrap(string, line_length, replace_whitespace=False)))
                        print("=" * line_length)
                        print("")

    elif report_type == "stats":
        labels = defaultdict(int)

        for commit in commits.split("\n"):
            pr = re.match('.*[#](\d+).*', commit)
            if pr:
                pr_number = int(pr.groups()[0].replace("#", ''))
                if pr_number in prs:
                    labels[prs[pr_number]['label']] += 1

        for label in labels:
            print("{}, {}".format(label, labels[label]))


if __name__ == "__main__":
    main()
