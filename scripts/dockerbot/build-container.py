from __future__ import absolute_import
import subprocess
import py
import sys

here = py.path.local(__file__).dirpath()


sys.exit(subprocess.call([
    'docker', 'build', '-t', 'py_test_base', str(here / 'pytestbase')
]))
