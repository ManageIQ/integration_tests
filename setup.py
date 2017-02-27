# dummy for editable installs
import sys
import os
from setuptools import setup, find_packages

# just cleanly exit on readthedocs
if os.environ.get('READTHEDOCS', None) == 'True':
    sys.exit()
elif 'develop' in sys.argv or 'egg_info' in sys.argv:
    pass
else:
    sys.exit('this is a hack, use pip install -e')

setup(
    name='manageiq-integration-tests',
    entry_points={
        'console_scripts': [
            'cfme-audit-navigatables = cfme.tools.audit_navigatables:main',
        ],
    },
    packages=find_packages(),
)
