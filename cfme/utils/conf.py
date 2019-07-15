import sys

from cfme.test_framework.config import Configuration
from cfme.utils import path

# in case this needs to be imported globally for Configuration.get_config() use
global_configuration = Configuration()

# Module impersonation to support from cfme.utils.conf import <name>
sys.modules[__name__] = global_configuration.configure(
    config_dir=path.conf_path.strpath,
    key_file=path.project_path.join('.yaml_key').strpath,
)
