import sys

from cfme.utils.config_copy import ConfigWrapper
from cfme.utils.config_copy import Configuration

sys.modules[__name__] = ConfigWrapper(Configuration())
