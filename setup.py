# dummy for editable installs
import sys
from setuptools import setup
assert 'develop' in sys.argv or 'egg_info' in sys.argv, \
    'this is a hack, use pip install -e'

setup(
    name='manageiq-integration-tests',
    packages=[],
)
