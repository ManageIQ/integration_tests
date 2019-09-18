import sys

from cfme.utils.config_copy import Configuration
from cfme.utils.config_copy import ConfigWrapper

sys.modules[__name__] = ConfigWrapper(Configuration())
