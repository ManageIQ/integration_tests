from __future__ import unicode_literals
import sys

from yaycl import Config

from utils import path

yaycl_options = {
    'config_dir': path.conf_path.strpath
}

# Look for the .yaml_key file, use it if it exists
crypt_key_file = path.project_path.join('.yaml_key')
if crypt_key_file.exists():
    yaycl_options['crypt_key_file'] = crypt_key_file.strpath

# Replace this module with the yaycl conf
sys.modules[__name__] = Config(**yaycl_options)
