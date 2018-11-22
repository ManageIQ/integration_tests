#!/usr/bin/env python2
from cfme.utils import conf
import subprocess
import sys
import re


def main():
    commit = sys.argv[1]

    key_list = [key.replace(" ", "") for key in conf["gpg"]["allowed_keys"]]
    proc = subprocess.Popen(
        ["git", "verify-commit", commit], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    proc.wait()
    output = proc.stderr.read()
    if re.findall("^gpg: Good signature", output, re.M):
        gpg = re.findall("fingerprint: ([A-F0-9 ]+)", output)[0].replace(" ", "")
        if gpg in key_list:
            print("Good sig and match for {}".format(gpg))
            sys.exit(0)
    print("ERROR: Bad signature. Please sign your commits!")
    sys.exit(127)


if __name__ == "__main__":
    main()
