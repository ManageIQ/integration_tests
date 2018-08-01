# dummy for editable installs
# don't mind me
import sys

import os
from setuptools import setup

ALLOWED_COMMANDS = {'develop', 'egg_info', 'bdist_wheel', 'sdist'}

# just cleanly exit on readthedocs
if os.environ.get('READTHEDOCS') == 'True':
    sys.exit()
elif ALLOWED_COMMANDS.intersection(sys.argv):
    pass
else:
    sys.exit('this is a hack, use pip install -e')

setup(
    setup_requires=['setuptools_scm>=3.0.0'],
    use_scm_version=True,
)
