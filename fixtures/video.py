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

from __future__ import unicode_literals
import os
import os.path
import pytest
import re

from utils.conf import env
from utils.path import log_path
from utils.video import Recorder

vid_options = env.get('logging', {}).get('video')
recorder = None


def get_path_and_file_name(node):
    """Extract filename and location from the node.

   Args:
       node: py.test collection node to examine.
   Returns: 2-tuple `(path, filename)`
   """
    vid_name = re.sub(r"[^a-zA-Z0-9_.\-\[\]]", "_", node.name)  # Limit only sane characters
    vid_name = re.sub(r"[/]", "_", vid_name)                    # To be sure this guy doesn't get in
    vid_name = re.sub(r"__+", "_", vid_name)                    # Squash _'s to limit the length
    return node.parent.name, vid_name


@pytest.mark.hookwrapper
def pytest_runtest_setup(item):
    global recorder
    if vid_options and vid_options['enabled']:
        vid_log_path = log_path.join(vid_options['dir'])
        vid_dir, vid_name = get_path_and_file_name(item)
        full_vid_path = vid_log_path.join(vid_dir)
        try:
            os.makedirs(full_vid_path.strpath)
        except OSError:
            pass
        vid_name = vid_name + ".ogv"
        recorder = Recorder(full_vid_path.join(vid_name).strpath)
        recorder.start()
    yield


def stop_recording():
    global recorder
    if recorder is not None:
        try:
            recorder.stop()
        finally:
            recorder = None


@pytest.mark.hookwrapper
def pytest_runtest_teardown(item, nextitem):
    yield
    stop_recording()


@pytest.mark.hookwrapper
def pytest_unconfigure(config):
    yield
    stop_recording()
