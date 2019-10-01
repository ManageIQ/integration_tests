import sys

from cfme.utils import path
from cfme.utils.config import ConfigWrapper
from cfme.utils.config import global_configuration

global_configuration.configure_creds(
    config_dir=path.conf_path.strpath,
    crypt_key_file=path.project_path.join('.yaml_key').strpath
)

sys.modules[__name__] = ConfigWrapper(global_configuration)
