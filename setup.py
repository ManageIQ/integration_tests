# dummy for editable installs
from __future__ import unicode_literals
import sys
import os
from setuptools import setup

# just cleanly exit on readthedocs
if os.environ.get('READTHEDOCS', None) == 'True':
    sys.exit()
elif 'develop' in sys.argv or 'egg_info' in sys.argv:
    pass
else:
    sys.exit('this is a hack, use pip install -e')

setup(
    name='manageiq-integration-tests',
    packages=[],
)
