#!/cfme_pristine_venv/bin/python2
try:
    from cfme.utils import conf
except ImportError:
    from utils import conf
import subprocess
import sys
import re

commit = sys.argv[1]

key_list = [key.replace(' ', '') for key in conf['gpg']['allowed_keys']]
proc = subprocess.Popen(['git', 'verify-commit', commit], stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
proc.wait()
output = proc.stderr.read()
print (output)
if re.findall('^gpg: Good signature', output, re.M):
    gpg = re.findall('fingerprint: ([A-F0-9 ]+)', output)[0].replace(' ', '')
    if gpg in key_list:
        print("Good sig and match for {}".format(gpg))
        sys.exit(0)
print("Bad sig")
sys.exit(127)
