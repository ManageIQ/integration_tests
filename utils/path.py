"""Project path helpers

Contains py.path.Local objects for accessing common project locations.

"""

import os

import py.path

_this_file = os.path.abspath(__file__)

project = py.path.local(_this_file).new(basename='..')
conf_path = project.join('conf')
data_path = project.join('data')
