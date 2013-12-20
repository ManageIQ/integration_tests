import sys

from utils.conf_loader import Config

sys.modules[__name__] = Config()
