import sys

from cfme.test_framework.config import (
    global_configuration,
    DeprecatedConfigWrapper,
)


from utils import path

global_configuration.configure(
    config_dir=path.conf_path.strpath,
    crypt_key_file=path.project_path.join('.yaml_key').strpath,
)

sys.modules[__name__] = DeprecatedConfigWrapper(global_configuration)
