from collections import defaultdict
import datetime
import requests

import subprocess
import re
import sys
from utils.conf import docker

full = True

new_ver = sys.argv[1]

if len(sys.argv) <= 2:
    proc = subprocess.Popen(['git', 'describe', '--tags', '--abbrev=0'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    old_tag = proc.stdout.read().strip("\n")
    major = False
else:
    old_tag = sys.argv[2]
    major = True
proc = subprocess.Popen(['git', 'log', '{}..master'.format(old_tag), '--oneline'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
commits = proc.stdout.read()

valid_labels = [
    u'fix-locator-or-text', u'infra-related', u'fix-test', u'doc',
    u'other', u'enhancement', u'fix-framework', u'new-test-or-feature'
]

print('integration_tests {} Released'.format(new_ver))
print('')
print('Includes: {} -> {}'.format(old_tag, new_ver))

max_len = len(reduce((lambda x, y: x if len(x) > len(y) else y), valid_labels))


now = datetime.date.today()
day_no = now.weekday()
start_of_week = now - datetime.timedelta(days=15)
string_start = start_of_week.strftime('%Y-%m-%d')

glob_lab = defaultdict(int)

headers = {'Authorization': 'token {}'.format(docker['gh_token'])}
r = requests.get(
    'https://api.github.com/search/issues?per_page=200&q=type:pr+repo:{}/'
    '{}+merged:>{}'.format(docker['gh_owner'], docker['gh_repo'], string_start),
    headers=headers)

prs = {}
for pr in r.json()['items']:
    prs[pr['number']] = pr
    for label in pr['labels']:
        if label['name'] in valid_labels:
            pr['label'] = label['name']


def clean_commit(commit_msg):
    replacements = ['1LP', 'RFR', 'WIP', 'WIPTEST', 'NOTEST']
    for replacement in replacements:
        commit_msg = commit_msg.replace('[{}]'.format(replacement), '')
    return commit_msg.strip(" ")


for commit in commits.split("\n"):
    pr = re.match('.*[#](\d+).*', commit)
    if pr:
        pr_number = int(pr.groups()[0].replace("#", ''))
        if pr_number in prs:
            old_lab = prs[pr_number]['label']
            label = old_lab + " " * (max_len - len(old_lab))
            msg = "{} | {} | {}".format(
                pr_number, label, clean_commit(prs[pr_number]['title']))
            if full:
                print "=" * len(msg)
            print msg
            if full:
                print "-" * len(msg)
                string = prs[pr_number]['body']
                pytest_match = re.findall("({{.*}}\s*)", string, flags=re.S | re.M)
                if pytest_match:
                    string = string.replace(pytest_match[0], '')
                print string
                print "=" * len(msg)
                print ("")
