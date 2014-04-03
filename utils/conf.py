import sys

from utils._conf import Config

sys.modules[__name__] = Config(__file__)
