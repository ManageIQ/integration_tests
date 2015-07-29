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
    def __init__(self, filename, display=None, quality=None, rtype=None, encoder=None):
        self.filename = filename
        self.display = display or vid_options["display"]
        self.quality = quality or vid_options["quality"]
        self.encoder = encoder
        self.rtype = rtype or "xfb"
        self.pid = None

    def start(self):
        if self.rtype == "xfb":
            cmd_line = ['recordmydesktop',
                        '--display', str(self.display),
                        '-o', str(self.filename),
                        '--no-sound',
                        '--v_quality', str(self.quality),
                        '--on-the-fly-encoding',
                        '--overwrite']
        elif self.rtype == "vnc":
            cmd_line = ['vncrec',
                        '-record', str(self.filename + ".tmp"),
                        '-viewonly',
                        '-shared',
                        '-depth', '16',
                        str(self.display)]
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

    def encode(self):
        if self.rtype == "vnc":
            c_string = self.encoder.replace('$file', self.filename)
            cmd_line = c_string.split(" ")
            cmd_line = ['vncrec', '-movie', self.filename + ".tmp", '|'] + cmd_line
            try:
                proc = subprocess.Popen(" ".join(cmd_line), stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, shell=True)
                proc.wait()
                os.remove(self.filename + ".tmp")
            except OSError:
                # Had to disable for artifactor
                # logger.exception("Couldn't initialize videoer! Is recordmydesktop installed?")
                pass

    def __enter__(self):
        self.start()

    def __exit__(self, t, v, tb):
        self.stop()

    def __del__(self):
        """If the reference is lost and the object is destroyed ..."""
        self.stop()
