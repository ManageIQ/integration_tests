""" Provides video options

Yaml example:
    .. code-block:: yaml

        logging:
           video:
               enabled: True
               dir: video
               display: ":99"
               quality: 10
"""

import os
import os.path
import pytest
import re
import signal
import subprocess

from utils.conf import env
from utils.path import log_path

vid_options = env.get('logging', {}).get('video')


def get_path_and_file_name(node):
    """Extract filename and location from the node.

   Args:
       node: py.test collection node to examine.
   Returns: 2-tuple `(path, filename)`
   """
    vid_name = re.sub(r"[^a-zA-Z0-9_.\-\[\]]", "_", node.name)  # Limit only sane characters
    vid_name = re.sub(r"[/]", "_", vid_name)                    # To be sure this guy don't get in
    vid_name = re.sub(r"__+", "_", vid_name)                    # Squash _'s to limit the length
    return node.parent.name, vid_name


@pytest.mark.tryfirst
def pytest_runtest_setup(item):
    if vid_options and vid_options['enabled']:
        vid_log_path = log_path.join(vid_options['dir'])
        vid_dir, vid_name = get_path_and_file_name(item)
        full_vid_path = vid_log_path.join(vid_dir)
        try:
            os.makedirs(str(full_vid_path))
        except OSError:
            pass
        filename = str(full_vid_path.join(vid_name))
        cmd_line = ['recordmydesktop',
                    '--display', vid_options['display'],
                    '-o', filename,
                    '--no-sound',
                    '--v_quality', vid_options['display'],
                    '--on-the-fly-encoding',
                    '--overwrite']
        try:
            proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with open(str(vid_log_path.join('pid')), "w") as f:
                f.write(str(proc.pid))
        except OSError:
            print "Couldn't initialize videoer"


@pytest.mark.trylast
def pytest_runtest_teardown(item, nextitem):
    if vid_options and vid_options['enabled']:
        vid_log_path = log_path.join(vid_options['dir'])
        with open(str(vid_log_path.join('pid')), "r") as f:
            pid = int(f.read())
        os.kill(pid, signal.SIGHUP)
