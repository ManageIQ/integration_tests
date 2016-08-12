"""Video recording library

Configuration for this module + fixture:
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
import subprocess

from signal import SIGINT

from utils.conf import env
# from utils.log import logger

vid_options = env.get('logging', {}).get('video')


def process_running(pid):
    """Check whether specified process is running"""
    try:
        os.kill(pid, 0)
    except OSError as e:
        if e.errno == 3:
            return False
        else:
            raise
    else:
        return True


class Recorder(object):
    """Recorder class

    Usage:

        with Recorder(filename):
            # do something

        # or
        r = Recorder(filename)
        r.start()
        # do something
        r.stop()

    The first way is preferred, obviously
    """
    def __init__(self, filename, display=None, quality=None):
        self.filename = filename
        self.display = display or vid_options["display"]
        self.quality = quality or vid_options["quality"]
        self.pid = None

    def start(self):
        cmd_line = ['recordmydesktop',
                    '--display', str(self.display),
                    '-o', str(self.filename),
                    '--no-sound',
                    '--v_quality', str(self.quality),
                    '--on-the-fly-encoding',
                    '--overwrite']
        try:
            proc = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.pid = proc.pid
        except OSError:
            # Had to disable for artifactor
            # logger.exception("Couldn't initialize videoer! Is recordmydesktop installed?")
            pass

    def stop(self):
        if self.pid is not None:
            if process_running(self.pid):
                os.kill(self.pid, SIGINT)
                os.waitpid(self.pid, 0)
                # Had to disable for artifactor
                # logger.info("Recording finished")
                self.pid = None
            else:
                # Had to disable for artifactor
                # logger.exception("Could not find recordmydesktop process #%d" % self.pid)
                pass

    def __enter__(self):
        self.start()

    def __exit__(self, t, v, tb):
        self.stop()

    def __del__(self):
        """If the reference is lost and the object is destroyed ..."""
        self.stop()
