import subprocess
import re
import sys

new_ver = sys.argv[1]

print('integration_tests {} Released'.format(new_ver))
print('')
print('Includes:')

if len(sys.argv) <= 2:
    proc = subprocess.Popen(['git', 'describe', '--tags', '--abbrev=0'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    old_tag = proc.stdout.read().strip("\n")
else:
    old_tag = sys.argv[2]
proc = subprocess.Popen(['git', 'log', '{}..master'.format(old_tag), '--oneline'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
commits = proc.stdout.read()
for commit in commits.split("\n"):
    if re.match('.*[#]\d+.*', commit):
        print(commit)
