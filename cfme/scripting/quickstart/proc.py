import os
import subprocess
import sys
from pipes import quote


PRISTINE_ENV = dict(os.environ)
if PRISTINE_ENV.get('CFME_QUICKSTART_DEBUG'):
    _call = subprocess.check_call
else:
    _call = subprocess.check_output


def command_text(command, shell):
    if shell:
        return command
    else:
        return ' '.join(map(quote, command))


def run_cmd_or_exit(command, shell=False, long_running=False,
                    call=_call, **kw):
    res = None
    try:
        if long_running:
            print(
                'QS $', command_text(command, shell),
                '# this may take some time to finish ...')
        else:
            print('QS $', command_text(command, shell))
        res = call(command, shell=shell, **kw)
    except Exception as e:
        print("Running command failed!")
        print(repr(e))
        sys.exit(1)
    return res
