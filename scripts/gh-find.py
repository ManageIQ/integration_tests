#!/usr/bin/env python2

from __future__ import unicode_literals
import argparse
import subprocess
import sys
import re
from collections import defaultdict


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('master', nargs='?', default='master',
        help='master branch')
    parser.add_argument('topic', nargs='?', default='downstream-stable',
        help='topic branch')
    args = parser.parse_args()
    print args.topic, args.master
    cmd_params = ['git', 'cherry', args.topic, args.master, '-v']
    proc = subprocess.Popen(cmd_params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()
    lc_info = proc.stdout.readlines()
    commits = []
    for line in lc_info:
        if line.startswith('+'):
            commits.append(re.search('(?:[-+]\s)([a-f0-9]+)(?:\s.*)', line).groups()[0])
    PRs = defaultdict(list)
    for commit in commits:
        cmd = ['git', 'log', '--merges', '--ancestry-path', '--oneline',
            '{}..master'.format(commit)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
        lcinfo = proc.stdout.readlines()
        lines = lcinfo[::-1]
        for line in lines:
            pr = re.search('(?:.+\sMerge pull request #)(\d+)(?:\sfrom)', line).groups()[0]
            if pr:
                PRs[pr].append(commit)
                break

    for PR in PRs:
        print "{} missing, contains:".format(PR)
        for commit in PRs[PR]:
            print "  {}".format(commit)

if __name__ == '__main__':
    sys.exit(main())
