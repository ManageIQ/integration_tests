#!/usr/bin/env python2
from coverage import CoverageData, misc
from utils.path import project_path
import sys
import subprocess
import re


def compute_coverage(branch):
    coverage_data = CoverageData()
    try:
        coverage_data.read_file(project_path.join('.coverage').strpath)
    except misc.CoverageException:
        sys.stderr.write("No coverage data found")

    git_proc = subprocess.Popen(['git', 'diff', '-U0', branch],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    git_output = git_proc.stdout.read()
    files = git_output.split("diff --git")

    from collections import defaultdict
    file_data = defaultdict(list)

    for the_file in files:
        filenames = re.findall('a/(.*?) b/(.*)', the_file)
        if not filenames:
            continue
        filename = project_path.join(filenames[0][1])
        if '.py' not in filename.strpath:
            continue
        the_file += "git_output_checker"
        the_diffs = re.findall('(@@.*?@@.*?(?=@@|git_output_checker))', the_file, re.M | re.S, )
        for diff in the_diffs:
            diff_args = re.match('@@ -(\d+)(,(\d+))*\s+\+(\d+)(,(\d+))*', diff).groups()
            if diff_args[5]:
                for extra_line in range(int(diff_args[5])):
                    file_data[filename].append(extra_line + int(diff_args[3]))
            else:
                file_data[filename].append(int(diff_args[3]))

    line_count = 0
    completed_lines = 0
    for file_changed, lines in file_data.iteritems():
        for line in lines:
            line_count += 1
            used_lines = coverage_data.lines(file_changed)
            if not used_lines:
                continue
            if isinstance(used_lines, int):
                used_lines = set([used_lines])
            else:
                used_lines = set(used_lines)
            if line in used_lines:
                completed_lines += 1

    return float(completed_lines) / line_count * 100


if __name__ == "__main__":
    result = compute_coverage(sys.argv[1])
    with open(project_path.join('coverage_result.txt').strpath, "w") as f:
        f.write("{}".format(result))
